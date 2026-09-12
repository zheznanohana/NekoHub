<template>
  <section class="memory-chat">
    <header><h2>记忆工作台</h2><p>Chat Agent · 图谱记忆 · 日 / 周 / 月回忆</p></header>
    <div class="toolbar">
      <button @click="send('/memory.search ' + JSON.stringify({text:''}))">记录</button>
      <button @click="send('/memory.graph {}')">关系图</button>
      <button @click="send('/memory.export {}')">结构化表格</button>
      <button @click="send('/memory.recall ' + JSON.stringify({text:''}))">回忆摘要</button>
      <button @click="send('/memory.daily {}')">整理日报</button>
      <button @click="process">处理一条记忆</button>
      <button @click="sync('gotify')">同步 Gotify</button>
      <button @click="sync('github')">同步 GitHub</button>
      <button @click="loadDiary">日记表</button>
      <button v-if="status.legacy_import_available" @click="importLegacy">导入旧版数据</button>
      <button @click="reindex">重建检索索引</button>
    </div>
    <p class="hint">{{ status.llm_configured ? 'LLM 已配置' : 'LLM 未配置：可先用斜杠命令增删改查' }} ·
      检索：{{ status.retrieval === 'hybrid' ? '关键词 + 语义（' + status.embed_model + '）' : '关键词 BM25（未配置向量模型，换个说法可能查不到）' }} ·
      Agent 仅建议删除，确认权在你。</p>
    <p v-if="error" role="alert">{{ error }}</p>
    <div class="messages" aria-live="polite">
      <article v-for="(message, mi) in messages" :key="mi" class="message">
        <p v-if="message.user" class="user">{{ message.user }}</p>
        <template v-for="(block, bi) in message.blocks || []" :key="bi">
          <p v-if="block.type === 'text'">{{ block.text }}</p>
          <div v-else-if="block.type === 'memory.cards'" class="cards">
            <p v-if="!block.items.length">没有匹配记录。</p>
            <article v-for="item in block.items" :key="item.id" class="card">
              <small>{{ item.occurred_at || '原文' }} · {{ item.id }}</small><p>{{ item.text }}</p>
              <button @click="edit(item)">修改</button>
              <button @click="send('/memory.delete ' + JSON.stringify({event_id:item.id}))">申请删除</button>
            </article>
          </div>
          <div v-else-if="block.type === 'memory.summaries'">
            <article v-for="item in block.items" :key="item.id" class="card">
              <strong>{{ item.level }} · {{ item.period }} · UTC</strong><p>{{ item.summary }}</p>
              <button @click="send('/memory.expand ' + JSON.stringify({summary_id:item.id}))">展开原始记录（{{ item.event_ids.length }}）</button>
            </article>
          </div>
          <div v-else-if="block.type === 'memory.action'" class="card action">
            <strong>待你确认：{{ block.command.command }}</strong>
            <p v-if="block.preview">原文／内容：{{ block.preview }}</p>
            <p v-if="block.reason">建议理由：{{ block.reason }} · 关联事实 {{ block.affected_facts }} 条</p>
            <pre>{{ JSON.stringify(block.command, null, 2) }}</pre>
            <p>确认后执行；删除会从检索隐藏原文及关联事实，当前为软删除，不擦除备份。</p>
            <button :disabled="used.has(block.action_id) || busy" @click="confirm(block)">{{ used.has(block.action_id) ? '已确认' : '确认执行' }}</button>
            <button :disabled="used.has(block.action_id)" @click="used.add(block.action_id)">保留 / 忽略</button>
          </div>
          <div v-else-if="block.type === 'memory.table'">
            <button @click="download(block)">导出 JSON</button><small>{{ block.scope }}</small>
            <button @click="tableMode='horizontal'">横向：字段表格</button><button @click="tableMode='vertical'">纵向：记录详情</button>
            <div v-if="tableMode==='horizontal'" style="overflow-x:auto"><table><thead><tr><th v-for="column in block.columns" :key="column">{{ column }}</th></tr></thead>
              <tbody><tr v-for="row in block.rows" :key="row.id"><td v-for="column in block.columns" :key="column"><template v-if="column==='evidence_ids'"><button v-for="id in row.evidence_ids" :key="id" @click="openEvent(id)">打开原文 {{ id.slice(0,8) }}</button></template><template v-else>{{ Array.isArray(row[column]) ? row[column].join(', ') : row[column] }}</template></td></tr></tbody>
            </table></div>
            <div v-else><article v-for="row in block.rows" :key="row.id" class="card"><dl><template v-for="column in block.columns" :key="column"><dt>{{ column }}</dt><dd>{{ Array.isArray(row[column]) ? row[column].join(', ') : row[column] }}</dd></template></dl><button v-for="id in row.evidence_ids" :key="id" @click="openEvent(id)">打开原文 {{ id.slice(0,8) }}</button></article></div>
          </div>
          <div v-else-if="block.type === 'memory.diary'" class="diary">
            <p class="hint">{{ block.scope }}</p>
            <p v-if="!block.rows.length">还没有任何一天的记录。先导入数据，或直接写今天的日记。</p>
            <div class="diary-split">
              <div style="overflow:auto;max-height:420px">
                <table><thead><tr><th>日期</th><th>日记</th><th>记录</th><th>来源</th></tr></thead>
                  <tbody><tr v-for="row in block.rows" :key="row.day" :class="{picked: diaryDay===row.day}" @click="pickDay(row)">
                    <td>{{ row.day }}</td><td>{{ row.text || '（未写）' }}</td>
                    <td>{{ row.event_count }}</td><td>{{ row.sources.join(' / ') }}</td>
                  </tr></tbody>
                </table>
              </div>
              <div>
                <label for="diary-day">日期</label>
                <input id="diary-day" v-model="diaryDay" placeholder="YYYY-MM-DD" />
                <label for="diary-text">我的日记</label>
                <textarea id="diary-text" v-model="diaryText" rows="6" placeholder="写下这一天。你写的内容优先于自动摘要。" />
                <button :disabled="busy || !diaryDay || !diaryText.trim()" @click="saveDiary">保存日记</button>
                <template v-if="diaryRow(block)">
                  <p class="hint">{{ diaryRow(block).version ? '第 ' + diaryRow(block).version + ' 版 · ' + (diaryRow(block).updated_at || '').slice(0,16) : '尚未写过' }} · 保存会保留上一版历史</p>
                  <details v-if="diaryRow(block).summary"><summary>当日自动摘要（只读）</summary><p>{{ diaryRow(block).summary }}</p></details>
                  <button v-for="id in diaryRow(block).event_ids.slice(0,6)" :key="id" @click="openEvent(id)">打开原文 {{ id.slice(0,8) }}</button>
                </template>
              </div>
            </div>
            <button @click="download(block)">导出 JSON</button>
          </div>
          <div v-else-if="block.type === 'memory.network'" class="graph">
            <div class="graph-bar">
              <span class="hint">{{ block.nodes.length }} 个节点 · {{ block.edges.length }} 条连接 · 圆点越大连接越多</span>
              <label><input type="checkbox" v-model="showLabels" /> 显示标签</label>
              <button @click="net(block).reheat()">重新排布</button>
              <button @click="net(block).fit()">适应画布</button>
              <button @click="download(block)">导出 JSON</button>
            </div>
            <p v-if="!block.nodes.length">暂无节点；先导入记录或整理摘要。</p>
            <svg v-else class="canvas" :viewBox="net(block).box.value" role="img" aria-label="记忆网络"
                 @wheel.prevent="net(block).zoom($event)" @pointerdown="net(block).panStart($event)"
                 @pointermove="net(block).pointerMove($event)" @pointerup="net(block).pointerUp()"
                 @pointerleave="net(block).pointerUp()">
              <line v-for="(edge, ei) in net(block).edges" :key="'e'+ei" :class="[edge.kind, {lit: net(block).lit(edge)}]"
                    :x1="edge.a.x" :y1="edge.a.y" :x2="edge.b.x" :y2="edge.b.y">
                <title>{{ EDGE_NAME[edge.kind] || edge.kind }}：{{ edge.label }}</title>
              </line>
              <g v-for="point in net(block).points" :key="point.id" class="node"
                 :opacity="net(block).dim(point.id) ? 0.22 : 1"
                 @pointerdown.stop="net(block).grab($event, point)">
                <circle :class="'level-' + point.level" :cx="point.x" :cy="point.y" :r="point.r"
                        :stroke-width="selected === point.id ? 3 : 1.5" />
                <title>{{ LEVEL_NAME[point.level] || point.level }} · {{ point.label }}</title>
                <text v-if="showLabels" :x="point.x" :y="point.y + point.r + 12" text-anchor="middle">{{ point.label.slice(0,14) }}</text>
              </g>
            </svg>
            <p class="hint">实线：下层压缩成上层摘要 · 虚线：实体之间的已确认关系 · 点线：事实指向原文证据。
              拖节点、滚轮缩放、拖空白平移。位置只是画法，连接才是数据。</p>
            <article v-if="picked(block)" class="card">
              <strong>{{ LEVEL_NAME[picked(block).level] || picked(block).level }} · {{ picked(block).label }}</strong>
              <p>{{ picked(block).text }}</p>
              <button @click="send('/memory.node.expand ' + JSON.stringify({node_id:selected,direction:'both'}))">展开相邻层级</button>
              <button v-if="picked(block).level!=='raw'" @click="send('/memory.expand ' + JSON.stringify({summary_id:selected}))">展开原始记录</button>
              <button v-for="id in picked(block).evidence_ids.slice(0,6)" :key="id" @click="openEvent(id)">打开原文 {{ id.slice(0,8) }}</button>
            </article>
          </div>
          <div v-else-if="block.type === 'memory.graph'" class="graph">
            <p v-if="!block.data.facts.length">暂无已确认图谱；先处理记录并审核。</p>
            <svg v-else viewBox="0 0 720 420" role="img" aria-label="记忆关系图">
              <g v-for="fact in block.data.facts.filter(f => f.object.node_id)" :key="fact.id">
                <line :x1="point(block.data,fact.subject_id).x" :y1="point(block.data,fact.subject_id).y" :x2="point(block.data,fact.object.node_id).x" :y2="point(block.data,fact.object.node_id).y" />
                <title>{{ fact.predicate }} — {{ fact.evidence.map(e=>e.quote).join('；') }}</title>
              </g>
              <g v-for="node in block.data.nodes" :key="node.id">
                <circle :cx="point(block.data,node.id).x" :cy="point(block.data,node.id).y" r="20" />
                <text :x="point(block.data,node.id).x" :y="point(block.data,node.id).y+36" text-anchor="middle">{{ node.label.slice(0,14) }}</text>
              </g>
            </svg>
            <article v-for="fact in block.data.facts" :key="fact.id" class="card">
              <strong>{{ label(block.data,fact.subject_id) }} → {{ fact.predicate }} → {{ fact.object.node_id ? label(block.data,fact.object.node_id) : fact.object.value }}</strong>
              <p>{{ fact.epistemic }} · {{ fact.status }}</p>
              <details><summary>原文证据</summary><p v-for="e in fact.evidence" :key="e.event_id">{{ e.quote }} <small>{{ e.event_id }}</small></p></details>
            </article>
          </div>
          <pre v-else-if="block.type === 'memory.receipt'">{{ JSON.stringify(block.data,null,2) }}</pre>
        </template>
      </article>
    </div>
    <form @submit.prevent="send()">
      <label for="memory-input">聊天或固定命令</label>
      <textarea id="memory-input" v-model="input" rows="3" placeholder='记住我今天开始整理项目，或 /memory.create {"text":"今天开始整理项目"}' />
      <button :disabled="busy || !input.trim()">{{ busy ? '处理中…' : '发送' }}</button>
    </form>
    <details class="connectors" :open="connectorsOpen" @toggle="connectorsOpen=$event.target.open">
      <summary>连接器 · 连接其他来源（{{ connectors.items.length }}）</summary>
      <p class="hint">凭据只向服务端单向写入，列表永远不回显，模型也读不到。</p>
      <table v-if="connectors.items.length"><thead><tr><th>来源</th><th>配置</th><th>上次</th><th>操作</th></tr></thead>
        <tbody><tr v-for="item in connectors.items" :key="item.id">
          <td>{{ kindLabel(item.kind) }}<br /><small>{{ item.name }}</small></td>
          <td><small>{{ Object.values(item.config).join(' · ') }}{{ item.has_secret ? ' · 已存凭据' : '' }}</small></td>
          <td><small>{{ item.last_result || '尚未运行' }}</small></td>
          <td>
            <button :disabled="busy" @click="runConnector(item.id)">立即拉取</button>
            <button :disabled="busy" @click="toggleConnector(item)">{{ item.enabled ? '停用' : '启用' }}</button>
            <button :disabled="busy" @click="removeConnector(item)">移除</button>
          </td>
        </tr></tbody>
      </table>
      <p v-else class="hint">还没有连接器。选择一种来源添加：</p>
      <div class="connector-form">
        <label for="connector-kind">来源类型</label>
        <select id="connector-kind" v-model="draft.kind" @change="draft.config={};draft.secret=''">
          <option v-for="k in connectors.kinds" :key="k.kind" :value="k.kind">{{ k.label }}</option>
        </select>
        <template v-if="kindSpec">
          <p class="hint">{{ kindSpec.note }}</p>
          <template v-for="field in kindSpec.fields" :key="field.name">
            <label :for="'cf-'+field.name">{{ field.label }}{{ field.optional ? '（可选）' : '' }}</label>
            <input :id="'cf-'+field.name" v-model="draft.config[field.name]" :placeholder="field.placeholder || ''" />
          </template>
          <template v-if="kindSpec.secret">
            <label for="cf-secret">{{ kindSpec.secret.label }}</label>
            <input id="cf-secret" v-model="draft.secret" type="password" autocomplete="new-password" />
          </template>
          <button :disabled="busy || !draft.kind" @click="addConnector">添加连接器</button>
        </template>
      </div>
    </details>
    <details><summary>待审核记忆 / 队列</summary>
      <article v-for="job in status.jobs || []" :key="job.id" class="card">
        {{ job.id }} · {{ job.state }} <span v-if="job.error">{{ job.error }}</span>
        <button v-if="job.state==='review'" @click="preview(job.id)">查看建议</button>
        <template v-if="proposals[job.id]">
          <pre>{{ JSON.stringify(proposals[job.id],null,2) }}</pre>
          <button :disabled="busy || job.state !== 'review'" @click="review(job.id,true)">确认记忆变更</button>
          <button :disabled="busy || job.state !== 'review'" @click="review(job.id,false)">拒绝</button>
        </template>
      </article>
    </details>
  </section>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
const input=ref(''), busy=ref(false), error=ref(''), messages=ref([]), status=ref({}), used=reactive(new Set()), proposals=reactive({})
const tableMode=ref('horizontal'), selected=ref(''), showLabels=ref(true)
const viewContext=reactive({selected_ids:[],visible_ids:[],levels:[],query:''})
const LEVEL_NAME={raw:'原始记录',day:'日记忆',week:'周记忆',month:'月记忆',entity:'关联实体'}
const EDGE_NAME={compresses:'压缩汇总',association:'实体关联',evidence:'原文证据'}

// One live force simulation per rendered network block, keyed by identity so a
// re-render does not restart the layout the user is already looking at.
const sims=new WeakMap()
function net(block){
  if(!sims.has(block)) sims.set(block, createNetwork(block))
  return sims.get(block)
}
function createNetwork(block){
  const W=900, H=560
  const points=reactive(block.nodes.map((n,i)=>{
    // Golden-angle seeding: spread out from the first frame, no random jitter.
    const a=i*2.399963229728653, span=40+300*Math.sqrt((i+0.5)/Math.max(block.nodes.length,1))
    const degree=block.edges.filter(e=>e.source===n.id||e.target===n.id).length
    const base={month:17,week:14,day:12,entity:11}[n.level] ?? 7
    return {...n, x:W/2+Math.cos(a)*span, y:H/2+Math.sin(a)*span, vx:0, vy:0,
            degree, r:base+2.6*Math.sqrt(degree), fixed:false}
  }))
  const byId=Object.fromEntries(points.map(p=>[p.id,p]))
  const edges=reactive(block.edges.filter(e=>byId[e.source]&&byId[e.target])
    .map(e=>({...e, a:byId[e.source], b:byId[e.target]})))
  const neighbours={}
  for(const e of edges){
    (neighbours[e.source] ??= new Set()).add(e.target)
    ;(neighbours[e.target] ??= new Set()).add(e.source)
  }
  viewContext.visible_ids=block.nodes.map(n=>n.id).slice(0,500)
  viewContext.levels=[...new Set(block.nodes.map(n=>n.level))]
  const view=reactive({x:0, y:0, w:W, h:H})
  const box=computed(()=>`${view.x} ${view.y} ${view.w} ${view.h}`)
  let alpha=1, frame=null, drag=null, pan=null

  function step(){
    alpha*=0.985
    const cell=110
    const buckets=new Map()
    for(const p of points){
      const key=`${Math.floor(p.x/cell)},${Math.floor(p.y/cell)}`
      ;(buckets.get(key) ?? buckets.set(key,[]).get(key)).push(p)
    }
    for(const p of points){
      let fx=0, fy=0
      const cx=Math.floor(p.x/cell), cy=Math.floor(p.y/cell)
      for(let dx=-1;dx<=1;dx++) for(let dy=-1;dy<=1;dy++){
        for(const q of buckets.get(`${cx+dx},${cy+dy}`) ?? []){
          if(q===p) continue
          let ox=p.x-q.x, oy=p.y-q.y, d2=ox*ox+oy*oy
          if(d2===0){ ox=0.5; oy=0.5; d2=0.5 }
          if(d2>cell*cell*4) continue
          const d=Math.sqrt(d2), push=9000*(1+0.32*q.degree)/d2
          fx+=ox/d*push; fy+=oy/d*push
        }
      }
      fx-=(p.x-W/2)*0.006; fy-=(p.y-H/2)*0.006
      p.vx=(p.vx+fx)*0.86; p.vy=(p.vy+fy)*0.86
    }
    for(const e of edges){
      const ox=e.b.x-e.a.x, oy=e.b.y-e.a.y
      const d=Math.hypot(ox,oy)||0.01, pull=0.012*(d-95)
      const ux=ox/d*pull*30, uy=oy/d*pull*30
      e.a.vx+=ux/(1+0.32*e.a.degree); e.a.vy+=uy/(1+0.32*e.a.degree)
      e.b.vx-=ux/(1+0.32*e.b.degree); e.b.vy-=uy/(1+0.32*e.b.degree)
    }
    for(const p of points){
      if(p.fixed){ p.vx=0; p.vy=0; continue }
      const speed=Math.hypot(p.vx,p.vy)
      if(speed>28){ p.vx*=28/speed; p.vy*=28/speed }
      p.x+=p.vx*alpha; p.y+=p.vy*alpha
    }
    frame = alpha>0.02 ? requestAnimationFrame(step) : null
  }
  function run(){ if(!frame && points.length) frame=requestAnimationFrame(step) }
  run()

  function svgPoint(event){
    const rect=event.currentTarget?.getBoundingClientRect?.() || event.target.ownerSVGElement.getBoundingClientRect()
    return {x:view.x+(event.clientX-rect.left)/rect.width*view.w,
            y:view.y+(event.clientY-rect.top)/rect.height*view.h}
  }
  return {
    points, edges, box,
    fit(){
      if(!points.length) return
      const pad=70
      const xs=points.map(p=>p.x), ys=points.map(p=>p.y)
      view.x=Math.min(...xs)-pad; view.y=Math.min(...ys)-pad
      view.w=Math.max(...xs)-Math.min(...xs)+pad*2
      view.h=Math.max(...ys)-Math.min(...ys)+pad*2
    },
    reheat(){ alpha=1; run() },
    zoom(event){
      const factor=event.deltaY>0 ? 1.12 : 1/1.12
      const at=svgPoint(event)
      view.x=at.x-(at.x-view.x)*factor; view.y=at.y-(at.y-view.y)*factor
      view.w*=factor; view.h*=factor
    },
    grab(event, point){
      selected.value=point.id
      viewContext.selected_ids=[point.id]
      drag={point, ...svgPoint(event)}
      point.fixed=true
      event.target.ownerSVGElement?.setPointerCapture?.(event.pointerId)
    },
    panStart(event){ pan={...svgPoint(event), x0:view.x, y0:view.y} },
    pointerMove(event){
      if(drag){
        const at=svgPoint(event)
        drag.point.x=at.x; drag.point.y=at.y
        alpha=Math.max(alpha,0.25); run()
      } else if(pan){
        const at=svgPoint(event)
        view.x=pan.x0-(at.x-pan.x); view.y=pan.y0-(at.y-pan.y)
      }
    },
    pointerUp(){ if(drag) drag.point.fixed=false; drag=null; pan=null },
    lit(edge){ return selected.value && (edge.source===selected.value || edge.target===selected.value) },
    dim(id){ return selected.value && id!==selected.value && !(neighbours[selected.value]?.has(id)) },
  }
}
function picked(block){return block.nodes.find(n=>n.id===selected.value)}
const base='/api/memory/v1'
async function call(path, data) {
  const r=await fetch(base+path,{method:data===undefined?'GET':'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+localStorage.getItem('token')},body:data===undefined?undefined:JSON.stringify(data)})
  const value=await r.json(); if(!r.ok) throw new Error(value.message || '请求失败'); return value
}
const diaryDay=ref(''), diaryText=ref('')
function diaryRow(block){return block.rows.find(r=>r.day===diaryDay.value)}
function pickDay(row){diaryDay.value=row.day;diaryText.value=row.text}
async function loadDiary(){await operation(()=>call('/diary'))}
async function saveDiary(){await operation(()=>call('/diary',{day:diaryDay.value,text:diaryText.value.trim()}))}
async function importLegacy(){await operation(()=>call('/import/legacy',{}))}
async function reindex(){await operation(()=>call('/reindex',{}))}

const connectors=reactive({kinds:[],items:[]}), connectorsOpen=ref(false)
const draft=reactive({kind:'',config:{},secret:''})
const kindSpec=computed(()=>connectors.kinds.find(k=>k.kind===draft.kind))
function kindLabel(kind){return connectors.kinds.find(k=>k.kind===kind)?.label || kind}
async function loadConnectors(){
  const value=await call('/connectors')
  connectors.kinds=value.kinds; connectors.items=value.items
  if(!draft.kind && connectors.kinds.length) draft.kind=connectors.kinds[0].kind
}
async function addConnector(){
  await operation(async()=>{
    const receipt=await call('/connectors',{kind:draft.kind,config:{...draft.config},secret:draft.secret})
    draft.config={}; draft.secret=''            // never keep a typed credential around
    await loadConnectors()
    return receipt
  })
}
async function runConnector(id){await operation(async()=>{const v=await call('/connectors/'+id+'/run',{});await loadConnectors();return v})}
async function toggleConnector(item){await operation(async()=>{const v=await call('/connectors/'+item.id,{enabled:!item.enabled});await loadConnectors();return v})}
async function removeConnector(item){
  if(!window.confirm('移除连接器「'+item.name+'」？已导入的记录会保留。')) return
  await operation(async()=>{const v=await callDelete('/connectors/'+item.id);await loadConnectors();return v})
}
async function callDelete(path){
  const r=await fetch(base+path,{method:'DELETE',headers:{Authorization:'Bearer '+localStorage.getItem('token')}})
  const value=await r.json(); if(!r.ok) throw new Error(value.message || '请求失败'); return value
}
async function refresh(){ status.value=await call('/status') }
async function operation(fn){if(busy.value)return;busy.value=true;error.value='';try{const v=await fn();if(v?.kind==='chat.blocks')messages.value.push(v);await refresh()}catch(e){error.value=e.message}finally{busy.value=false}}
async function send(value){const text=typeof value==='string'?value:input.value;if(!text.trim()||busy.value)return;messages.value.push({user:text});input.value='';await operation(()=>call('/chat',{schema_version:'1.0',message:text,view_context:{...viewContext,query:input.value||viewContext.query}}))}
async function confirm(block){await operation(async()=>{const v=await call('/actions/'+block.action_id+'/confirm',{});used.add(block.action_id);return v})}
async function process(){await operation(()=>call('/process',{}))}
async function sync(source){await operation(()=>call('/sync/'+source,{}))}
async function preview(id){await operation(async()=>{proposals[id]=(await call('/jobs/'+id)).proposal})}
async function review(id,approve){await operation(()=>call('/jobs/'+id+'/review',{approve}))}
async function openEvent(id){await operation(async()=>{const data=await call('/events/'+id);return {kind:'chat.blocks',blocks:[{type:'memory.cards',items:[{id,text:data.content.text,occurred_at:data.occurred_at}]}]}})}
function edit(item){input.value='/memory.update '+JSON.stringify({event_id:item.id,text:item.text})}
function download(block){const url=URL.createObjectURL(new Blob([JSON.stringify({schema_version:'1.0',kind:block.type+'.export',...block},null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='nekohub-memory.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
function label(graph,id){return graph.nodes.find(n=>n.id===id)?.label || id}
function point(graph,id){const i=graph.nodes.findIndex(n=>n.id===id),n=graph.nodes.length,a=2*Math.PI*i/Math.max(n,1);return {x:360+260*Math.cos(a),y:195+135*Math.sin(a)}}
onMounted(()=>Promise.all([refresh(),loadConnectors()]).catch(e=>error.value=e.message))
</script>

<style scoped>
.memory-chat{max-width:1000px;margin:auto;color:var(--text-primary)}
.toolbar{display:flex;gap:8px;flex-wrap:wrap}.hint,small{color:var(--text-secondary)}
button{padding:9px 13px;margin:4px;border:1px solid var(--border-color);background:var(--bg-primary);color:var(--text-primary);border-radius:7px;cursor:pointer}button:disabled{opacity:.5;cursor:default}
.message,.card{padding:16px;margin:12px 0;border:1px solid var(--border-color);border-radius:10px;background:var(--bg-primary)}
.user{font-weight:600}.action{border-left:4px solid var(--primary-color)}
p,pre{white-space:pre-wrap;overflow-wrap:anywhere}pre{font-size:12px}small{word-break:break-all}
textarea{box-sizing:border-box;width:100%;padding:12px;border:1px solid var(--border-color);background:var(--bg-primary);color:var(--text-primary);border-radius:8px;font:inherit}
svg{width:100%;max-height:460px}line{stroke:var(--border-color);stroke-width:2}circle{fill:var(--primary-color)}text{fill:var(--text-primary);font-size:12px}
.graph-bar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:6px}
.graph-bar label{display:flex;gap:5px;align-items:center;color:var(--text-secondary)}
svg.canvas{width:100%;height:min(62vh,520px);max-height:none;background:#0f1a24;border-radius:10px;touch-action:none;cursor:grab}
svg.canvas line{stroke:#3f5f70;stroke-width:1.4}
svg.canvas line.association{stroke:#7a6bab;stroke-dasharray:6 4}
svg.canvas line.evidence{stroke:#3f5f70;stroke-dasharray:2 4;opacity:.55}
svg.canvas line.lit{stroke:#8fe6cc;stroke-width:2.6;opacity:1}
svg.canvas text{fill:#c7d7e6;font-size:11px;pointer-events:none;user-select:none}
.node{cursor:pointer}.node circle{stroke:#0f1a24}
circle.level-raw{fill:#6f92b8}circle.level-day{fill:#6fc4a8}circle.level-week{fill:#e8c15c}
circle.level-month{fill:#f0a35a}circle.level-entity{fill:#a08ae8}
.connectors{margin:14px 0;padding:14px;border:1px solid var(--border-color);border-radius:10px}
.connectors summary{cursor:pointer;font-weight:600}
.connector-form{display:grid;gap:2px;max-width:520px}
.connector-form label{margin-top:8px;color:var(--text-secondary)}
.connector-form input,.connector-form select{box-sizing:border-box;width:100%;padding:9px;border:1px solid var(--border-color);background:var(--bg-primary);color:var(--text-primary);border-radius:7px;font:inherit}
.connector-form button{margin-top:12px;justify-self:start}
.diary-split{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:16px}
@media (max-width:760px){.diary-split{grid-template-columns:1fr}}
.diary tbody tr{cursor:pointer}.diary tbody tr.picked{background:var(--bg-secondary,rgba(127,127,127,.14))}
.diary input{box-sizing:border-box;width:100%;padding:9px;border:1px solid var(--border-color);background:var(--bg-primary);color:var(--text-primary);border-radius:7px;font:inherit}
.diary label{display:block;margin:10px 0 4px;color:var(--text-secondary)}
th,td{text-align:left;vertical-align:top;padding:8px;border-bottom:1px solid var(--border-color);min-width:90px;max-width:400px;overflow-wrap:anywhere}
</style>
