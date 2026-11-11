import json

with open("e:/Concrete-design/profiles.json", "r", encoding="utf-8") as f:
    data = json.load(f)

test_tank = data.get("profiles", {}).get("Test tank", {})
m10_keys = {k: v for k, v in test_tank.items() if "m10" in k}
print("PROFILES TEST TANK:")
for k, v in sorted(m10_keys.items()):
    print(f"  {k}: {v}")

with open("e:/Concrete-design/user_settings.json", "r", encoding="utf-8") as f:
    u_data = json.load(f)
u_m10_keys = {k: v for k, v in u_data.items() if "m10" in k}
print("\nUSER_SETTINGS TEST TANK:")
for k, v in sorted(u_m10_keys.items()):
    print(f"  {k}: {v}")
