from fastapi import FastAPI
from backend.app.simulator.scenario import generate_scenario, ScenarioConfig
from backend.app.state.repository import EventStore

app = FastAPI(title="MOSAIC Control Tower API")

# In-memory fast projection
current_state = None
event_store = EventStore("mosaic.db")

@app.on_event("startup")
def startup_event():
    global current_state
    # Initialize with a default deterministic scenario on startup for the hackathon
    config = ScenarioConfig(seed=58291)
    current_state = generate_scenario(config)
    print(f"MOSAIC Engine Started. State Version: {current_state.state_version}")

@app.get("/state")
def get_state():
    return current_state

@app.post("/scenario/reset")
def reset_scenario(seed: int = 58291):
    global current_state
    config = ScenarioConfig(seed=seed)
    current_state = generate_scenario(config)
    return {"message": "Scenario reset", "seed": seed, "state_version": current_state.state_version}
