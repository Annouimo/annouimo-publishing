const labels = { question: '问题', example: '例题', note: '注', tip: '提示', warning: '注意', important: '重要', info: '信息', quote: '引用', abstract: '摘要', success: '完成', failure: '失败', bug: '问题' };

export default function remarkCallouts() {
  function visit(node) {
    if (!node || typeof node !== 'object') return;
    if (node.type === 'blockquote') {
      const paragraph = node.children?.[0];
      const first = paragraph?.children?.[0];
      if (first?.type === 'text') {
        const match = first.value.match(/^\[!([\w-]+)\]([+-])?([^\n]*)(?:\n|$)/);
        if (match) {
          const title = match[3].trim() || labels[match[1].toLowerCase()] || match[1];
          first.value = first.value.slice(match[0].length);
          if (!first.value) paragraph.children.shift();
          if (!paragraph.children.length) node.children.shift();
          node.data = { ...node.data, hName: match[2] ? 'details' : 'aside', hProperties: { className: ['callout'], ...(match[2] === '+' ? { open: true } : {}) } };
          node.children.unshift({ type: 'paragraph', data: { hName: match[2] ? 'summary' : 'div', hProperties: { className: ['callout-title'] } }, children: [{ type: 'text', value: title }] });
        }
      }
    }
    for (const child of node.children || []) visit(child);
  }
  return tree => visit(tree);
}
