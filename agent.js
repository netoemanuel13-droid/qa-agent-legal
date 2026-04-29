import Anthropic from '@anthropic-ai/sdk';
import fs from 'fs';
import path from 'path';

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const CONTENT_DIR = './qa_content';

if (!fs.existsSync(CONTENT_DIR)) {
  fs.mkdirSync(CONTENT_DIR, { recursive: true });
}

// Tool definitions for Q&A content management
const tools = [
  {
    name: 'save_qa_content',
    description: 'Save a Q&A content item for TikTok publication. Call this after generating each Q&A pair.',
    input_schema: {
      type: 'object',
      properties: {
        topic:      { type: 'string', description: 'Topic or category of the Q&A' },
        question:   { type: 'string', description: 'The attention-grabbing question' },
        answer:     { type: 'string', description: 'Concise answer optimized for TikTok (max 150 words)' },
        hashtags:   { type: 'array', items: { type: 'string' }, description: '3–5 relevant TikTok hashtags' },
        difficulty: { type: 'string', enum: ['easy', 'medium', 'hard'], description: 'Content difficulty level' },
      },
      required: ['topic', 'question', 'answer', 'hashtags'],
    },
  },
  {
    name: 'list_qa_content',
    description: 'List all saved Q&A content items, optionally filtered by topic.',
    input_schema: {
      type: 'object',
      properties: {
        topic_filter: { type: 'string', description: 'Optional substring filter on topic name' },
      },
    },
  },
  {
    name: 'get_qa_content',
    description: 'Retrieve a specific saved Q&A item by its ID.',
    input_schema: {
      type: 'object',
      properties: {
        id: { type: 'string', description: 'The content item ID (e.g. qa_1234567890)' },
      },
      required: ['id'],
    },
  },
];

// ── Tool implementations ──────────────────────────────────────────────────────

function saveQaContent(input) {
  const id = `qa_${Date.now()}`;
  const record = { id, ...input, created_at: new Date().toISOString() };
  fs.writeFileSync(path.join(CONTENT_DIR, `${id}.json`), JSON.stringify(record, null, 2));
  return { success: true, id, message: `Saved Q&A content as ${id}` };
}

function listQaContent({ topic_filter } = {}) {
  if (!fs.existsSync(CONTENT_DIR)) return { items: [], count: 0 };
  const items = fs
    .readdirSync(CONTENT_DIR)
    .filter(f => f.endsWith('.json'))
    .map(f => JSON.parse(fs.readFileSync(path.join(CONTENT_DIR, f), 'utf8')));
  const filtered = topic_filter
    ? items.filter(i => i.topic.toLowerCase().includes(topic_filter.toLowerCase()))
    : items;
  return { items: filtered, count: filtered.length };
}

function getQaContent({ id }) {
  const filePath = path.join(CONTENT_DIR, `${id}.json`);
  if (!fs.existsSync(filePath)) return { error: `No content found with ID: ${id}` };
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function executeTool(name, input) {
  switch (name) {
    case 'save_qa_content':  return saveQaContent(input);
    case 'list_qa_content':  return listQaContent(input);
    case 'get_qa_content':   return getQaContent(input);
    default:                 return { error: `Unknown tool: ${name}` };
  }
}

// ── Cached system prompt ──────────────────────────────────────────────────────
// Placed in a separate array so cache_control can be applied once and reused
// across all requests in this process, keeping input_tokens low after the first call.

const SYSTEM = [
  {
    type: 'text',
    text: `You are QA Agent Bot, an AI specialized in creating viral Q&A content for TikTok.

## Your Mission
Generate engaging, educational question-and-answer pairs that are optimized for short-form video content and designed to be saved and published automatically.

## Content Guidelines
- Questions must be intriguing, surprising, or challenge a common misconception
- Answers must be concise (≤150 words) and immediately understandable
- Each post needs 3–5 relevant hashtags
- Content should work as a TikTok caption or spoken script
- Mix educational, entertaining, and trending angles

## Supported Categories
Science & Technology | History & Culture | Psychology & Behavior |
Nature & Wildlife | Food & Health | Business & Finance | Fun Facts & Trivia

## Workflow
For every Q&A pair you create:
1. Write a hook question
2. Write a clear, punchy answer with a surprising fact or takeaway
3. Add context that makes viewers want to share it
4. Pick hashtags that match the topic and current TikTok trends
5. Call save_qa_content to persist the item`,
    cache_control: { type: 'ephemeral' }, // cached for 5 min; subsequent calls read from cache
  },
];

// ── Core generation loop ──────────────────────────────────────────────────────

async function generateQaContent(topic, count = 3) {
  console.log(`\n🤖 Generating ${count} Q&A post(s) about: "${topic}"\n`);

  const messages = [
    {
      role: 'user',
      content: `Generate ${count} unique, high-quality Q&A content items about "${topic}" for TikTok. Use the save_qa_content tool for each one.`,
    },
  ];

  let finalResponse;

  // Agentic loop — continue until the model stops requesting tools
  while (true) {
    const stream = client.messages.stream({
      model: 'claude-sonnet-4-6',
      max_tokens: 4096,
      system: SYSTEM,
      tools,
      messages,
    });

    // Stream text output to the console in real time
    stream.on('text', text => process.stdout.write(text));

    finalResponse = await stream.finalMessage();

    if (finalResponse.stop_reason === 'end_turn') {
      console.log('\n\n✅ Generation complete.');
      break;
    }

    if (finalResponse.stop_reason === 'tool_use') {
      const toolUseBlocks = finalResponse.content.filter(b => b.type === 'tool_use');

      // Append the assistant turn before sending tool results
      messages.push({ role: 'assistant', content: finalResponse.content });

      const toolResults = toolUseBlocks.map(tu => {
        console.log(`\n🔧 ${tu.name}(${JSON.stringify(tu.input).slice(0, 60)}…)`);
        const result = executeTool(tu.name, tu.input);
        if (result.success) console.log(`   ✓ ${result.message}`);
        if (result.error)   console.error(`   ✗ ${result.error}`);
        return { type: 'tool_result', tool_use_id: tu.id, content: JSON.stringify(result) };
      });

      messages.push({ role: 'user', content: toolResults });
      continue;
    }

    // pause_turn or unexpected stop — break to avoid infinite loop
    break;
  }

  // Report token usage so callers can verify prompt caching is working
  if (finalResponse?.usage) {
    const u = finalResponse.usage;
    console.log('\n📊 Token usage:');
    console.log(`   Input:          ${u.input_tokens}`);
    console.log(`   Output:         ${u.output_tokens}`);
    if (u.cache_creation_input_tokens) console.log(`   Cache written:  ${u.cache_creation_input_tokens}`);
    if (u.cache_read_input_tokens)     console.log(`   Cache read:     ${u.cache_read_input_tokens}`);
  }

  return finalResponse;
}

// ── CLI helpers ───────────────────────────────────────────────────────────────

function printContent(topicFilter) {
  const { items, count } = listQaContent({ topic_filter: topicFilter });
  console.log(`\n📋 Saved Q&A content — ${count} item(s)${topicFilter ? ` (filter: "${topicFilter}")` : ''}:\n`);
  for (const item of items) {
    console.log(`[${item.id}]  ${item.topic}  (${item.difficulty ?? 'n/a'})`);
    console.log(`  Q: ${item.question}`);
    console.log(`  A: ${item.answer.slice(0, 120)}${item.answer.length > 120 ? '…' : ''}`);
    console.log(`  #: ${item.hashtags.join('  ')}`);
    console.log();
  }
}

// ── Entry point ───────────────────────────────────────────────────────────────

async function main() {
  if (!process.env.ANTHROPIC_API_KEY) {
    console.error('❌  ANTHROPIC_API_KEY environment variable is not set.');
    console.error('    Copy .env.example to .env and add your key.');
    process.exit(1);
  }

  const [command = 'generate', arg1, arg2] = process.argv.slice(2);

  switch (command) {
    case 'generate':
      await generateQaContent(arg1 ?? 'science facts', Number(arg2) || 3);
      break;
    case 'list':
      printContent(arg1);
      break;
    default:
      console.log('Usage:');
      console.log('  node agent.js generate [topic] [count]   — generate Q&A content');
      console.log('  node agent.js list     [topic_filter]    — list saved content');
  }
}

main().catch(err => { console.error(err); process.exit(1); });
