import matplotlib.pyplot as plt

w2 = [[0.2969794, 0.41460723, 0.06508236, 0.00458173],
      [-0.46137148, -0.35638228, -0.17965679, 0.2596846],
      [-0.24496864, -0.2912518, -0.04233079, -0.37715995],
      [0.35630783, 0.2516995, 0.49515975, 0.1285058],
      [0.49753636, 0.54680747, 0.02442583, 0.53564215],
      [-0.59238625, -0.4037412, -0.02377657, 0.21364462],
      [-0.15655074, 0.06968993, -0.3729832, -0.05259628],
      [-0.03103397, -0.16530576, 0.05211098, -0.3233184],
      [0.42573535, 0.37263402, 0.11522491, 0.6661805],
      [-0.20440614, -0.15345223, -0.50020057, -0.5194988],
      [-0.27666482, -0.39497972, -0.35336876, -0.28332222],
      [-0.14985253, -0.4792609, -0.08786384, -0.13125893],
      [0.14495769, -0.16200508, -0.13200319, -0.2460582],
      [-0.10929127, -0.47405005, -0.53231627, 0.21174346],
      [-0.08864505, -0.29220626, -0.37661862, -0.47474667],
      [-0.48953232, -0.03493555, -0.30371693, -0.19974704],
      [-0.18150142, -0.24763094, 0.08106827, 0.4797563],
      [-0.25764492, -0.0055915, -0.4007022, -0.32181928],
      [-0.12392386, 0.11531496, 0.5163047, 0.4222704],
      [-0.38943952, -0.3045076, 0.03241422, 0.02763436],
      [-0.4632193, 0.02696685, -0.54621273, -0.10847716],
      [0.50617594, 0.40117565, 0.44027913, 0.2887015],
      [0.00690778, -0.0293262, -0.474544, -0.62609655],
      [0.00912726, -0.2006169, -0.42260328, -0.11707853],
      [0.504184, 0.4555369, -0.03677496, 0.47901672],
      [-0.16265495, -0.43702886, -0.44505703, -0.5575779]]
import numpy as np

# Assuming your file is named 'weights.txt' and contains the NumPy array representation
"""with open('weights.txt', 'r') as f:
    # Read the content, clean up brackets and newlines
    data_str = f.read().replace('[', '').replace(']', '').replace('\n', ' ')

# Use np.fromstring to convert the string to a 1D array of floats
# Then, reshape it to the original dimensions if needed
# and convert to a list

with open("weights.txt", 'r') as file:
  content = file.read()

# Pre-process the content: replace non-standard spaces and 'e' with 'E'
cleaned_content = content.replace('e', 'E').strip()
cleaned_content = cleaned_content.replace("[", " ").replace("]", " ")
cleaned_content = cleaned_content.replace("\n", " ")
arr = np.loadtxt(StringIO(cleaned_content))
# Safely evaluate the string to get a Python list
weights = arr

features = 100
hidden_dim = 128
features_contribution = [0]* features
for i in range(features):
  for j in range(hidden_dim):
    features_contribution[i] += abs(weights[i*128 + j])"""

features_contribution = [0.34554774, -0.22709945, -0.16181818, -0.15983918, 0.24281642, -0.13969907,
                         -0.04994936, 0.2117948, -0.33858424, 0.48846152, 0.13243218, 0.2784241,
                         -0.13677898, -0.45727944, -0.09317109, 0.2152072, 0.05758855, -0.1829744,
                         0.14606285, -0.4395219, -0.09248064, -0.08060396, 0.17833965, -0.37950385,
                         -0.1176933, -0.21872973, -0.28549576, -0.00461699, 0.01876737, 0.35117936,
                         0.15005913, 0.12462197, -0.2913651, -0.36044842, 0.09130919, -0.01872326,
                         -0.23522833, -0.06078664, -0.27819353, 0.06169851, -0.3998643, 0.20906477,
                         0.26173955, 0.2386803, -0.09962429, 0.2094239, 0.04365398, 0.04194833,
                         -0.05373843, 0.1026874, 0.05476128, 0.31909582, -0.3098439, -0.24411109,
                         -0.17476542, 0.46698314, 0.0960795, 0.03542353, -0.04018841, 0.185763,
                         0.34976047, -0.128169, -0.12004751, 0.6300975, 0.19609214, 0.0482704,
                         0.03305284, -0.10869563, 0.07266103, -0.15389025, 0.10512552, 0.14874022,
                         0.5130478, -0.09988272, 0.2898111, -0.194128, -0.47651827, -0.33006483,
                         0.00328046, -0.23207071, -0.29030886, 0.0991624, -0.06860562, 0.08357331,
                         0.267496, -0.06526513, -0.28028476, -0.06908014, 0.11533336, 0.02652176,
                         -0.00284845, 0.00852492, 0.12443504, -0.11311238, -0.01396298, 0.12125093,
                         -0.0861202, -0.07447228, 0.32350978, -0.28369206]

values = np.abs(features_contribution)
values = values / np.max(values)
for i in range(len(features_contribution)):
    print(f"{i}:{values[i]}")
categories = list(range(len(features_contribution)))
plt.bar(np.arange(len(categories)), values, color=['skyblue', 'salmon', 'lightgreen', 'gold'])

# --- 3. Customize the chart with labels and a title ---
# Set the x-axis tick labels to the category names
plt.xticks(np.arange(len(categories)), categories)

# Add a title to the chart
plt.title('Weights Contributions')

# Label the y-axis
plt.ylabel('Values')

# Label the x-axis
plt.xlabel('Categories')

# Add a grid for better readability
plt.grid(axis='y', linestyle='--', alpha=0.7)

# --- 4. Display the chart ---
plt.show()
