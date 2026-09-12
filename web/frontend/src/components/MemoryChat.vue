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
    </div>
    <p class="hint">{{ status.llm_configured ? 'LLM 已配置' : 'LLM 未配置：可先用斜杠命令增删改查' }} · Agent 仅建议删除，确认权在你。</p>
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
          <div v-else-if="block.type === 'memory.network'" class="graph">
            <p class="hint">{{ block.scope }}</p>
            <p v-if="!block.nodes.length">暂无节点；先导入记录或整理摘要。</p>
            <svg v-else viewBox="0 0 720 460" role="img" aria-label="分层记忆网络">
              <g v-for="(edge, ei) in block.edges" :key="'e'+ei">
                <line :class="edge.kind" :x1="place(block,edge.source).x" :y1="place(block,edge.source).y"
                      :x2="place(block,edge.target).x" :y2="place(block,edge.target).y" />
                <title>{{ edge.label }}（{{ edge.kind }}）</title>
              </g>
              <g v-for="node in block.nodes" :key="node.id" @click="pick(block, node)" class="node">
                <circle :class="['level-'+node.level, selected===node.id ? 'picked' : '']"
                        :cx="place(block,node.id).x" :cy="place(block,node.id).y" :r="node.level==='raw' ? 11 : 17" />
                <title>{{ node.level }} · {{ node.label }}</title>
                <text :x="place(block,node.id).x" :y="place(block,node.id).y+30" text-anchor="middle">{{ node.label.slice(0,12) }}</text>
              </g>
            </svg>
            <p class="hint">实线向上汇总，虚线关联实体，点线指向原文证据。层级不是生物脑结构。</p>
            <article v-if="picked(block)" class="card">
              <strong>{{ picked(block).level }} · {{ picked(block).label }}</strong>
              <p>{{ picked(block).text }}</p>
              <button @click="send('/memory.node.expand ' + JSON.stringify({node_id:selected,direction:'both'}))">展开相邻层级</button>
              <button v-if="picked(block).level!=='raw'" @click="send('/memory.expand ' + JSON.stringify({summary_id:selected}))">展开原始记录</button>
              <button v-for="id in picked(block).evidence_ids.slice(0,6)" :key="id" @click="openEvent(id)">打开原文 {{ id.slice(0,8) }}</button>
            </article>
            <button @click="download(block)">导出 JSON</button>
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
import { ref, reactive, onMounted } from 'vue'
const input=ref(''), busy=ref(false), error=ref(''), messages=ref([]), status=ref({}), used=reactive(new Set()), proposals=reactive({})
const tableMode=ref('horizontal'), selected=ref('')
const viewContext=reactive({selected_ids:[],visible_ids:[],levels:[],query:''})
const LEVELS=['raw','day','week','month','entity']
function place(block,id){
  const node=block.nodes.find(n=>n.id===id); if(!node) return {x:360,y:230}
  // Rings encode level, not similarity: inner rings hold the more compressed nodes.
  const ring=Math.max(LEVELS.indexOf(node.level),0)
  const peers=block.nodes.filter(n=>n.level===node.level)
  const i=peers.findIndex(n=>n.id===id), a=2*Math.PI*i/Math.max(peers.length,1)
  const radius=[300,215,150,85,255][ring] ?? 200
  return {x:360+radius*Math.cos(a), y:230+radius*0.62*Math.sin(a)}
}
function picked(block){return block.nodes.find(n=>n.id===selected.value)}
function pick(block,node){
  selected.value = selected.value===node.id ? '' : node.id
  syncView(block)
}
function syncView(block){
  viewContext.selected_ids = selected.value ? [selected.value] : []
  viewContext.visible_ids = block.nodes.map(n=>n.id).slice(0,500)
  viewContext.levels = [...new Set(block.nodes.map(n=>n.level))]
}
const base='/api/memory/v1'
async function call(path, data) {
  const r=await fetch(base+path,{method:data===undefined?'GET':'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+localStorage.getItem('token')},body:data===undefined?undefined:JSON.stringify(data)})
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
onMounted(()=>refresh().catch(e=>error.value=e.message))
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
line.association{stroke-dasharray:6 4}line.evidence{stroke-dasharray:2 4;opacity:.6}
.node{cursor:pointer}circle.level-raw{fill:var(--text-secondary)}circle.level-entity{fill:#7a5af5}
circle.picked{stroke:var(--primary-color);stroke-width:4}
th,td{text-align:left;vertical-align:top;padding:8px;border-bottom:1px solid var(--border-color);min-width:90px;max-width:400px;overflow-wrap:anywhere}
</style>
