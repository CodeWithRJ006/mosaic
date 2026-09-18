import { useEffect, useState } from 'react'

function App() {
  const [message, setMessage] = useState<string>('Loading...')

  useEffect(() => {
    fetch('http://localhost:8000/health')
      .then(res => res.json())
      .then(data => setMessage(data.message))
      .catch(() => setMessage('Error connecting to backend'))
  }, [])

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="bg-white p-8 rounded-lg shadow-md text-center">
        <h1 className="text-2xl font-bold mb-4 text-blue-600">MOSAIC Control Tower</h1>
        <p className="text-lg text-gray-700 font-mono">Backend status: {message}</p>
      </div>
    </div>
  )
}

export default App
