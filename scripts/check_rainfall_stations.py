from defra_agent.storage.station_repo import StationMetadataRepository

repo = StationMetadataRepository()
count = repo._collection.count_documents({"source": "rainfall"})
print(f"Total rainfall stations in MongoDB: {count}")

test_ids = ["3680", "3275", "3167", "3307", "E7050"]
print(f"\nLooking for stations: {test_ids}")

for sid in test_ids:
    doc = repo.get_station("rainfall", sid)
    if doc:
        print(f'  ✓ {sid}: Found - lat={doc.get("lat")}, lon={doc.get("lon")}')
    else:
        print(f"  ✗ {sid}: Not found")

print("\nChecking if missing IDs exist in other sources...")
for sid in ["3680", "3275", "3167", "3307"]:
    for source in ["flood", "hydrology"]:
        doc = repo.get_station(source, sid)
        if doc:
            print(f"  {sid} found in {source}!")
