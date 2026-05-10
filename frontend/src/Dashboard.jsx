import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import './Dashboard.css'

function Dashboard() {
  const [name, setName] = useState('')
  const navigate = useNavigate()

  const handleEnter = (e) => {
    e.preventDefault()
    if (name.trim()) {
      // We can pass the name via state or just navigate
      navigate('/generate', { state: { projectName: name } })
    }
  }

  return (
    <div className="dashboard-simple">
      <div className="enter-container">
        <h1>Welcome to API-Genie</h1>
        <p>Enter your project name to get started</p>
        <form onSubmit={handleEnter} className="simple-form">
          <input 
            type="text" 
            placeholder="Your Project Name" 
            value={name} 
            onChange={(e) => setName(e.target.value)}
            autoFocus
          />
          <button type="submit" className="btn btn-primary">Enter</button>
        </form>
      </div>
    </div>
  )
}

export default Dashboard
