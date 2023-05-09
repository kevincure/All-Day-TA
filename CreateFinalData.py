import os
import pandas as pd
import numpy as np

csv_folder = "Textchunks"
npy_folder = "Embedded Text"

# Get the sorted list of CSV and .npy files
csv_files = sorted([f for f in os.listdir(csv_folder) if f.endswith('.csv')])
npy_files = sorted([f for f in os.listdir(npy_folder) if f.endswith('.npy')])

# Initialize empty DataFrame and NumPy array for concatenation
concatenated_csv = pd.DataFrame()
concatenated_npy = None

for csv_file, npy_file in zip(csv_files, npy_files):
    print(npy_file)
    # Read the CSV file and concatenate
    csv_path = os.path.join(csv_folder, csv_file)
    csv_data = pd.read_csv(csv_path, encoding='utf-8', escapechar='\\')
    concatenated_csv = pd.concat([concatenated_csv, csv_data], ignore_index=True)

    npy_path = os.path.join(npy_folder, npy_file)
    npy_data = np.load(npy_path)
    if concatenated_npy is None:
        concatenated_npy = npy_data
    else:
        concatenated_npy = np.concatenate([concatenated_npy, npy_data], axis=0)


# Save the concatenated data to the base folder
concatenated_csv.to_csv("textchunks-originaltext.csv", encoding='utf-8', escapechar='\\', index=False)
np.save("textchunks.npy", concatenated_npy)
print("Files saved: textchunks-originaltext.csv and textchunks.npy")
# Print the dimensions of the concatenated files
print(f"textchunks-originaltext.csv dimensions: {concatenated_csv.shape}")
print(f"textchunks.npy dimensions: {concatenated_npy.shape}")

