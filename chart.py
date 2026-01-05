import matplotlib.pyplot as plt
import pandas as pd

# Define the detailed data
data = {
    'Material': ['PLA Basic', 'PLA Matte', 'PLA Silk', 'PLA-CF', 'PETG Basic', 'PETG-CF', 'ABS', 'ASA', 'TPU 95A', 'PC', 'PAHT-CF'],
    'Nozzle Temp (°C)': ['190 - 230', '190 - 230', '210 - 240', '210 - 240', '230 - 260', '230 - 260', '240 - 270', '240 - 270', '210 - 240', '260 - 280', '260 - 290'],
    'Bed Temp (°C)': ['35 - 45', '35 - 45', '35 - 45', '45 - 65', '65 - 75', '65 - 75', '90 - 100', '90 - 100', '30 - 35', '90 - 110', '80 - 100'],
    'Part Fan (%)': ['100%', '100%', '100%', '50 - 100%', '20 - 50%', '20 - 50%', '0 - 20%', '0 - 20%', '100%', '0 - 20%', '0 - 20%'],
    'Drying Recom.': ['55°C (8h)', '55°C (8h)', '55°C (8h)', '55°C (8h)', '65°C (8h)', '65°C (8h)', '80°C (8h)', '80°C (8h)', '70°C (8h)', '80°C (8h)', '80°C (12h)'],
    'Density (g/cm³)': ['1.24', '1.31', '1.24', '1.26', '1.27', '1.29', '1.05', '1.07', '1.22', '1.20', '1.23'],
    'HDT (°C)': ['57', '55', '50', '55', '68', '74', '87', '100', 'N/A', '117', '194'],
    'Rec. Speed': ['< 300 mm/s', '< 200 mm/s', '< 150 mm/s', '< 150 mm/s', '< 200 mm/s', '< 150 mm/s', '< 300 mm/s', '< 200 mm/s', '< 30-60 mm/s', '< 250 mm/s', '< 100 mm/s'],
    'Enclosure': ['Open/Cool', 'Open/Cool', 'Open/Cool', 'Open/Cool', 'Optional', 'Optional', 'Required', 'Required', 'Open/Cool', 'Required', 'Required']
}

df = pd.DataFrame(data)

# Create the table plot
fig, ax = plt.subplots(figsize=(16, 8)) # Wider to fit columns
ax.axis('tight')
ax.axis('off')

# Define colors
header_color = '#008080' # Teal
row_colors = ['#f5f5f5', '#ffffff'] # Alternating row colors
edge_color = '#dddddd'

# Create the table
table = ax.table(cellText=df.values, colLabels=df.columns, loc='center', cellLoc='center')

# Styling
table.auto_set_font_size(False)
table.set_fontsize(11)
table.scale(1.2, 1.8) # Adjust scale for readability

# Header styling
for (row, col), cell in table.get_celld().items():
    if row == 0:
        cell.set_text_props(weight='bold', color='white')
        cell.set_facecolor(header_color)
        cell.set_edgecolor('white')
    else:
        cell.set_facecolor(row_colors[row % 2])
        cell.set_edgecolor(edge_color)
        cell.set_height(0.1) # More padding

# Add title
plt.title('Bambu Lab Filament Reference Guide', fontsize=18, weight='bold', pad=20, y=1.05, color='#333333')
plt.tight_layout()
plt.savefig('bambu_filament_reference_table.png', dpi=300, bbox_inches='tight')

# Save the table as an image
plt.savefig('bambu_filament_reference_table.png', dpi=300, bbox_inches='tight')