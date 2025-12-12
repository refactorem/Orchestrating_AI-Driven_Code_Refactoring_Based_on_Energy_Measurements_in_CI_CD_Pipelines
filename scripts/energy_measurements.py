import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

df = pd.read_csv("datos.csv")
df['measurement_index'] = df['measurement_index'].astype(int)

plt.rcParams.update({
    'font.size': 9,
    'lines.linewidth': 1.2,
    'lines.markersize': 4,
})

fig, ax = plt.subplots(figsize=(7.5, 4.5))

df = df[df['baseline'] == False]
versiones = ['original', 'AI-generated refactored version']

base_colors = {
    'original': mcolors.to_rgb('tab:blue'),
    'AI-generated refactored version': mcolors.to_rgb('tab:orange')
}

for version in versiones:
    grupo = df[df['version'] == version]
    if not grupo.empty:
        base = base_colors[version]
        pkg_color = tuple(min(1.0, c*0.8) for c in base)
        cores_color = tuple(min(1.0, c*1.2) for c in base)

        ax.plot(
            grupo['measurement_index'],
            grupo['energy_pkg_consumption'],
            label=f"{version}, pkg",
            color=pkg_color,
            linestyle='--',
            marker='x'
        )
        ax.plot(
            grupo['measurement_index'],
            grupo['energy_cores_consumption'],
            label=f"{version}, cores",
            color=cores_color,
            linestyle='-',
            marker='o'
        )
        
        pkg_mean = grupo['energy_pkg_consumption'].mean()
        cores_mean = grupo['energy_cores_consumption'].mean()

        ax.hlines(pkg_mean, grupo['measurement_index'].min(), grupo['measurement_index'].max(),
                  colors=pkg_color, linestyles=':', linewidth=1)
        ax.hlines(cores_mean, grupo['measurement_index'].min(), grupo['measurement_index'].max(),
                  colors=cores_color, linestyles='-.', linewidth=1)
        
        total_range = df[['energy_pkg_consumption', 'energy_cores_consumption']].max().max() - \
                      df[['energy_pkg_consumption', 'energy_cores_consumption']].min().min()
        offset = max(0.02 * total_range, 0.05)

        ax.text(grupo['measurement_index'].max()+0.5, pkg_mean + offset, f"{pkg_mean:.2f}", va='center', fontsize=8)
        ax.text(grupo['measurement_index'].max()+0.5, cores_mean - offset, f"{cores_mean:.2f}", va='center', fontsize=8)

x_min = df['measurement_index'].min()
x_max = df['measurement_index'].max()
ax.set_xlim(x_min, x_max + 2)

vline_indices = [1, 5, 10, 15, 20, 25, 30]
for xi in vline_indices:
    ax.axvline(x=xi, color='gray', linestyle=':', linewidth=0.8)

ax.set_xlabel('Measurement Index')
ax.set_ylabel('Energy Consumption (J)')
ax.set_title('Energy consumption: Comparing original vs AI-generated refactored version')

ax.legend(fontsize=8, loc='upper center', bbox_to_anchor=(0.5, -0.22),
          ncol=2, frameon=True, edgecolor='black')

ax.grid(True, linestyle=':', linewidth=0.5)
plt.tight_layout()
plt.savefig("energy_comparison.pdf", format='pdf', bbox_inches='tight')
plt.show()
