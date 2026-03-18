# analyze_dtmb.py
from motions_dtmb3_repo import MotionsDTMB3Repo
import matplotlib.pyplot as plt

repo = MotionsDTMB3Repo("./MotionsAndWaveData")

print(repo.summary())
print(repo.probe_locations())

# Load one motion file
df_roll = repo.load_motion(signal="R", state_code=124, seed=4)
repo.inspect_series(df_roll, rolling=100)

# Load one probe file
df_probe = repo.load_probe(axis="Y", state_code=124, seed=25, location=350)
repo.inspect_series(df_probe, rolling=100)

# Load one full case
ds = repo.load_case(state_code=124, seed=25)
print(ds)

# Plot roll
ds["roll"].plot()
plt.show()

# Plot one X-probe location
ds["probe_x"].sel(x_location=-200).plot()
plt.show()

# Compare one motion signal across all seeds
roll_all = repo.load_motion_matrix(signal="R", state_code=124)
mean_roll = roll_all.mean(dim="seed")
std_roll = roll_all.std(dim="seed")

mean_roll.plot()
plt.show()
