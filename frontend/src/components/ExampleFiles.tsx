function ExampleFiles() {
  const examples = [
    '报纸类.pdf',
    '繁体字杂志.pdf',
    '竖排文本.pdf',
    'PPT类.pdf',
    '复杂公式.png',
    '化学方程式.png',
    '含公式表格.jpg',
    '多栏文本.png',
    '手写文字.png',
    '中文公式.jpg',
    '复杂排版.png',
    '日文小说.png'
  ]

  return (
    <div className="examples">
      <h2>示例文件</h2>
      <ul>
        {examples.map((example, index) => (
          <li key={index}>{example}</li>
        ))}
      </ul>
    </div>
  )
}

export default ExampleFiles