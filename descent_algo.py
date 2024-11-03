import os
import subprocess
from datetime import datetime

simulate_script = "/homes/lp721/aca-gem5/simulate.py"

global instruction_windows, branch_predictors, reg_sizes, cache1_sizes, cache2_sizes, pipeline_depths

instruction_windows = [
    [16, 11, 5], [32, 21, 11], [64, 43, 21],
    [128, 85, 43], [256, 171, 85], [512, 341, 171]
]

branch_predictors = [
    [64, 128, 128, 16], [128, 256, 128, 16], [256, 512, 256, 16],
    [512, 1024, 512, 32], [1024, 2048, 1024, 32], [2048, 4096, 2048, 64],
    [4096, 8192, 4096, 128], [8192, 16384, 8192, 256]
]

reg_sizes = [2**i for i in range(6, 12)]
cache1_sizes = [2**i for i in range(2, 10)]
cache2_sizes = [2**i for i in range(2, 5)]
pipeline_depths = [2**i for i in range(2, 6)]

def run_simulation(iw, bp, ir, fr, vr, l1_d, l1_i, l2, pd):
    output_name = generate_output_name(iw, bp, ir, fr, vr, l1_d, l1_i, l2, pd)
    window_size_str = ",".join(map(str, instruction_windows[iw]))
    branch_size_str = ",".join(map(str, branch_predictors[bp]))
    command = [
        "python3", simulate_script,
        "--window-size", window_size_str,
        "--branch-pred-size", branch_size_str,
        "--num-int-phys-regs", str(reg_sizes[ir]),
        "--num-float-phys-regs", str(reg_sizes[fr]),
        "--num-vec-phys-regs", str(reg_sizes[vr]),
        "--l1-data-size", str(cache1_sizes[l1_d]),
        "--l1-inst-size", str(cache1_sizes[l1_i]),
        "--l2-size", str(cache2_sizes[l2]),
        "--pipeline-width", str(pipeline_depths[pd]),
        "--name", output_name
    ]
    subprocess.run(command)

def get_sim_energy(results_file_path):
    if os.path.isdir(results_file_path):
        results_file_path = os.path.join(results_file_path, "results")
        if os.path.isfile(results_file_path):
            try:
                with open(results_file_path, 'r') as file:
                    data = file.readlines()
                    file.close()

                # Initialize variables to store the extracted values
                simulated_seconds = 0.0
                subthreshold_leakage = 0.0
                gate_leakage = 0.0
                runtime_dynamic = 0.0
                
                # Extract each value from its corresponding line
                for line in data:
                    if "Energy" in line:
                        return float(line.split('=')[-1].strip().split()[0])
                    if "Simulated seconds" in line:
                        simulated_seconds = float(line.split('=')[1].strip())
                    elif "Subthreshold Leakage" in line:
                        subthreshold_leakage = float(line.split('=')[1].strip().split()[0])
                    elif "Gate Leakage" in line:
                        gate_leakage = float(line.split('=')[1].strip().split()[0])
                    elif "Runtime Dynamic" in line:
                        runtime_dynamic = float(line.split('=')[1].strip().split()[0])

                # Calculate energy
                energy = simulated_seconds * (subthreshold_leakage + gate_leakage + runtime_dynamic)
                with open(results_file_path, 'a') as file:
                    file.write(f"\nEnergy = {energy}\n")
                    file.close()
                    
                return energy
            
            except Exception as e:
                print(f"Error processing {results_file_path}: {e}")
                return None

def generate_output_name(iw, bp, ir, fr, vr, l1_d, l1_i, l2, pd):
    return (
        f"instr_{'_'.join(map(str, instruction_windows[iw]))}_"
        f"branch_{'_'.join(map(str, branch_predictors[bp]))}_"
        f"intRegs_{reg_sizes[ir]}_floatRegs_{reg_sizes[fr]}_"
        f"vecRegs_{reg_sizes[vr]}_l1Data_{cache1_sizes[l1_d]}_"
        f"l1Inst_{cache1_sizes[l1_i]}_l2_{cache2_sizes[l2]}_"
        f"pipeline_{pipeline_depths[pd]}"
    )
        
def decend(iw, bp, ir, fr, vr, l1_d, l1_i, l2, pd, visited, min_energy):
    
    def attempt_simulation(params,visited):
        next_name = generate_output_name(*params)
        folder_path = os.path.join(os.getcwd(), next_name)

        if next_name in visited or os.path.exists(folder_path):
            energy = get_sim_energy(folder_path) 
        else:
            visited += next_name 
            run_simulation(*params)
            energy = get_sim_energy(folder_path)
            
        return next_name, energy

    params = [iw, bp, ir, fr, vr, l1_d, l1_i, l2, pd]
    energies = []
    ps = []
    names = []

    bounds = [
        (0, len(instruction_windows) - 1),
        (0, len(branch_predictors) - 1),
        (0, len(reg_sizes) - 1),
        (0, len(reg_sizes) - 1),
        (0, len(reg_sizes) - 1),
        (0, len(cache1_sizes) - 1),
        (0, len(cache1_sizes) - 1),
        (0, len(cache2_sizes) - 1),
        (0, len(pipeline_depths) - 1)
    ]

    for idx, (lower_bound, upper_bound) in enumerate(bounds):

        if params[idx] > lower_bound:
            new_params = params.copy()
            new_params[idx] -= 1
            name, energy = attempt_simulation(new_params,visited)
            if name and energy is not None:
                energies.append(energy)
                names.append(name)
                ps.append(new_params)
                
        if params[idx] < upper_bound:
            new_params = params.copy()
            new_params[idx] += 1
            name, energy = attempt_simulation(new_params,visited)
            if name and energy is not None:
                energies.append(energy)
                names.append(name)
                ps.append(new_params)
                
    if min(energies) < min_energy:
        min_energy = min(energies)
        min_params = ps[energies.index(min_energy)]
        return decend(min_params[0], min_params[1], min_params[2], min_params[3], min_params[4], min_params[5], min_params[6], min_params[7], min_params[8], visited, min_energy)
    else:
        return min_energy, names[energies.index(min_energy)]


min_energy = get_sim_energy(os.path.join(os.getcwd(), generate_output_name(0, 0, 0, 0, 0, 0, 0, 0, 0)))

print(min_energy)
min_energy, min_name = decend(0, 0, 0, 0, 0, 0, 0, 0, 0, [], min_energy)

with open(f"ANSWER_{datetime.now()}.txt", 'w') as f:
    f.write(f"Energy: {min_energy}\nFile name:{min_name}\n")
    f.close()