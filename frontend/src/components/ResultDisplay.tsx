interface ResultDisplayProps {
  result: any
}

function ResultDisplay({ result }: ResultDisplayProps) {
  if (!result) return null

  return (
    <div className="result">
      <h2>识别结果</h2>
      <pre>{JSON.stringify(result, null, 2)}</pre>
    </div>
  )
}

export default ResultDisplay