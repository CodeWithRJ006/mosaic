from typing import List
from backend.app.models.state import NetworkState, CapacityOpportunity

def build_temporal_capacity_graph(state: NetworkState) -> List[CapacityOpportunity]:
    """
    Scans all vehicles in the network state and extracts explicit future 
    transportation capacity segments.
    This creates the Temporal Recovery Capacity Graph.
    """
    opportunities = []
    
    for v_id, vehicle in state.vehicles.items():
        for segment in vehicle.schedule:
            # For the exact capacity, we must calculate the load of all shipments
            # currently assigned to this vehicle for this specific segment.
            # (Simplified here for initial scaffolding)
            current_load_weight = 0.0 
            current_load_volume = 0.0
            
            # Find shipments that are planned to be on this vehicle during this segment
            for s_id, shipment in state.shipments.items():
                if shipment.current_location == v_id:
                    # In a full implementation, check if the shipment's path overlaps this segment
                    pass
            
            opportunities.append(CapacityOpportunity(
                vehicle_id=v_id,
                segment_id=segment.segment_id,
                from_node=segment.from_node,
                to_node=segment.to_node,
                arrival_time=segment.arrival_time,
                departure_time=segment.departure_time,
                available_weight=vehicle.max_weight - current_load_weight,
                available_volume=vehicle.max_volume - current_load_volume,
                route_direction=f"{segment.from_node}->{segment.to_node}"
            ))
            
    return opportunities
