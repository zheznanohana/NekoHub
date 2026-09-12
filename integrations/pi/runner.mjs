// Pi agent subprocess. Reads one config line, then exchanges tool JSON lines
// with the Python host. The host owns every tool implementation; this process
// only relays calls and never touches the filesystem, shell or database.
import {Agent} from '@earendil-works/pi-agent-core';
import {createModels, createProvider, envApiKeyAuth} from '@earendil-works/pi-ai';
import {openAICompletionsApi} from '@earendil-works/pi-ai/api/openai-completions.lazy';
import {createInterface} from 'node:readline';

const MAX_TOOLS = 8;
const MAX_TURNS = 10;
const RUN_TIMEOUT_MS = 120000;

const rl = createInterface({input: process.stdin});
const waiting = [];
const queue = [];
let closed = false;
rl.on('line', line => (waiting.length ? waiting.shift()(line) : queue.push(line)));
rl.on('close', () => {
  closed = true;
  while (waiting.length) waiting.shift()(null);
});
const read = () => (queue.length ? Promise.resolve(queue.shift()) : closed ? Promise.resolve(null) : new Promise(resolve => waiting.push(resolve)));
const write = value => process.stdout.write(JSON.stringify(value) + '\n');

function buildModel() {
  const id = process.env.MEMORY_LLM_MODEL;
  const baseUrl = process.env.MEMORY_LLM_BASE_URL;
  if (!id || !baseUrl) throw new Error('model configuration missing');
  return {
    id, name: id, api: 'openai-completions', provider: 'nekohub', baseUrl,
    reasoning: false, input: ['text'],
    cost: {input: 0, output: 0, cacheRead: 0, cacheWrite: 0},
    contextWindow: 64000, maxTokens: 4096,
    compat: {supportsStore: false, supportsDeveloperRole: false, maxTokensField: 'max_tokens'},
  };
}

try {
  const first = await read();
  if (first === null) throw new Error('no configuration received');
  const config = JSON.parse(first);
  const model = buildModel();
  const models = createModels();
  models.setProvider(createProvider({
    id: 'nekohub', name: 'NekoHub', baseUrl: model.baseUrl,
    auth: {apiKey: envApiKeyAuth('NekoHub memory model key', ['MEMORY_LLM_API_KEY'])},
    models: [model], api: openAICompletionsApi(),
  }));

  let count = 0;
  const tools = config.tools.map(spec => ({
    name: spec.name,
    label: spec.name,
    description: spec.description,
    parameters: spec.parameters,
    execute: async () => { throw new Error('unreachable'); },
  }));
  for (const [index, spec] of config.tools.entries()) {
    tools[index].execute = async (id, args) => {
      if (++count > MAX_TOOLS) throw new Error('tool budget reached');
      write({type: 'tool', name: spec.name, args});
      const line = await read();
      if (line === null) throw new Error('host closed the tool channel');
      const reply = JSON.parse(line);
      return {content: [{type: 'text', text: JSON.stringify(reply)}], details: {}};
    };
  }

  const agent = new Agent({
    streamFn: models.streamSimple.bind(models),
    initialState: {systemPrompt: config.system, model, tools},
    getApiKey: () => process.env.MEMORY_LLM_API_KEY,
    toolExecution: 'sequential',
  });
  let turns = 0;
  agent.subscribe(event => { if (event.type === 'turn_start' && ++turns > MAX_TURNS) agent.abort(); });
  const timer = setTimeout(() => agent.abort(), RUN_TIMEOUT_MS);
  try { await agent.prompt(JSON.stringify(config.input)); } finally { clearTimeout(timer); }

  const last = agent.state.messages.filter(m => m.role === 'assistant').at(-1);
  if (!last || last.stopReason === 'error' || last.stopReason === 'aborted') throw new Error('model run did not complete');
  write({type: 'final', text: last.content.filter(c => c.type === 'text').map(c => c.text).join('\n')});
} catch (error) {
  write({type: 'error', message: 'Pi runtime failed'});
  process.exitCode = 1;
} finally {
  rl.close();
  process.stdin.destroy();
}
