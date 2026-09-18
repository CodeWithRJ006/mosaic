import pytest
from app.simulator.scenario import ScenarioGenerator

def test_scenario_generator_determinism():
    seed = 42
    
    gen1 = ScenarioGenerator(seed)
    hubs1, vehicles1, shipments1 = gen1.generate()
    
    gen2 = ScenarioGenerator(seed)
    hubs2, vehicles2, shipments2 = gen2.generate()
    
    assert len(hubs1) == len(hubs2)
    assert len(vehicles1) == len(vehicles2)
    assert len(shipments1) == len(shipments2)
    
    # Assert byte-identical (or property-identical)
    for h1, h2 in zip(hubs1, hubs2):
        assert h1.id == h2.id
        assert h1.name == h2.name
        assert h1.lat == h2.lat
        assert h1.lon == h2.lon
        
    for v1, v2 in zip(vehicles1, vehicles2):
        assert v1.id == v2.id
        assert v1.max_weight == v2.max_weight
        assert v1.schedule == v2.schedule
        
    for s1, s2 in zip(shipments1, shipments2):
        assert s1.id == s2.id
        assert s1.weight == s2.weight
        assert s1.planned_route == s2.planned_route
