"""Geospatial Logistics & Supply Clustering for Mavuno."""
from __future__ import annotations
import secrets
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import FarmerProfile, Settlement
from sklearn.cluster import KMeans

def cluster_collection_routes(db: Session, n_clusters: int = 3) -> list[dict]:
    """
    Groups settled payments into geospatial clusters for collection optimization.
    Returns a list of routes with stops.
    """
    # 1. Fetch settled settlements with farm GPS coordinates
    stmt = select(
        Settlement.id.label("pid"), 
        Settlement.farm_id.label("fid"),
        FarmerProfile.farmer_name, 
        FarmerProfile.crop,
        FarmerProfile.lat,
        FarmerProfile.lng,
        Settlement.amount_ugx
    ).join(FarmerProfile, Settlement.farm_id == FarmerProfile.user_id).where(Settlement.status == 'settled')
    
    rows = db.execute(stmt).all()
    if not rows:
        return []

    data = [dict(r._mapping) for r in rows]
    
    # 2. Extract coordinates for clustering
    coords = np.array([[d['lat'], d['lng']] for d in data if d['lat'] is not None and d['lng'] is not None])
    
    if len(coords) < n_clusters:
        n_clusters = max(1, len(coords))

    # 3. Perform KMeans clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto').fit(coords)
    labels = kmeans.labels_
    centroids = kmeans.cluster_centers_

    # 4. Group data by cluster labels
    clusters = {}
    for i, label in enumerate(labels):
        cluster_id = int(label)
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(data[i])

    # 5. Format into routes
    routes = []
    for cid, stops in clusters.items():
        routes.append({
            "id": f"RT-{secrets.token_hex(2).upper()}-{cid}",
            "center": {"lat": float(centroids[cid][0]), "lng": float(centroids[cid][1])},
            "total_stops": len(stops),
            "stops": stops,
            "estimated_kg": sum([s.get('kg', 0) for s in stops]) # Note: kg might need to be joined too if needed
        })

    return routes
