import random
import numpy as np
from collections import namedtuple

try:
    from sklearn.ensemble import RandomForestRegressor
except Exception:
    # Fallback simple RandomForestRegressor stub when scikit-learn is not available.
    class RandomForestRegressor:
        def __init__(self, n_estimators=50):
            self.n_estimators = n_estimators
            self._trained = False
            self._samples = None
            self._costs = None

        def fit(self, X, y):
            # store training data; use mean as default prediction
            self._samples = [tuple(x) for x in X]
            self._costs = list(y)
            self._mean = float(np.mean(self._costs)) if len(self._costs) else 0.0
            self._trained = True
            return self

        def predict(self, X):
            if not self._trained:
                return [0.0 for _ in X]
            preds = []
            for x in X:
                tx = tuple(x)
                if self._samples and tx in self._samples:
                    preds.append(float(self._costs[self._samples.index(tx)]))
                else:
                    preds.append(self._mean)
            return np.array(preds)

VM = namedtuple('VM', ['name', 'ip', 'cpu_cores', 'ram_gb'])
Task = namedtuple('Task', ['id', 'name', 'index', 'cpu_load', 'ram_mb'])

# ---------------------------------------------
# COST FUNCTION 
# ---------------------------------------------
def calculate_estimated_makespan(solution: dict, tasks_dict: dict, vms_dict: dict) -> float:
    vm_loads = {vm.name: 0.0 for vm in vms_dict.values()}
    
    for task_id, vm_name in solution.items():
        task = tasks_dict[task_id]
        vm = vms_dict[vm_name]
        estimated_time = task.cpu_load / vm.cpu_cores
        vm_loads[vm_name] += estimated_time
        
    return max(vm_loads.values())


# RANDOM FOREST (RF) MODEL 

def build_rf_model(samples, costs):
    """Melatih Random Forest untuk memprediksi kualitas solusi."""
    rf = RandomForestRegressor(n_estimators=80)
    rf.fit(samples, costs)
    return rf

def encode_solution(solution, vm_names, task_ids):
    """Encode solusi menjadi vektor numerik agar bisa masuk ke RF."""
    encoding = []
    for task_id in task_ids:
        vm_name = solution[task_id]
        encoding.append(vm_names.index(vm_name))
    return encoding

# TUNICATE SWARM ALGORITHM (TSA) 
def tsa_rf(tasks: list[Task], vms: list[VM], iterations: int, population_size: int = 20):
    print(f"Memulai TSA-RF dengan {iterations} iterasi, populasi {population_size}...")

    # Persiapan
    vms_dict = {vm.name: vm for vm in vms}
    tasks_dict = {task.id: task for task in tasks}
    vm_names = list(vms_dict.keys())
    task_ids = [task.id for task in tasks]


    # 1. Bangun populasi awal (solusi acak)
    population = []
    for _ in range(population_size):
        sol = {t_id: random.choice(vm_names) for t_id in task_ids}
        population.append(sol)

    # 2. Hitung cost awal
    costs = [calculate_estimated_makespan(sol, tasks_dict, vms_dict) for sol in population]
    best_index = np.argmin(costs)
    best_solution = population[best_index]
    best_cost = costs[best_index]

    print(f"Makespan awal terbaik: {best_cost:.2f}")

    # 3. Persiapan RF Training Data
    sample_vectors = [encode_solution(population[i], vm_names, task_ids) for i in range(population_size)]
    rf = build_rf_model(sample_vectors, costs)

    # 4. Iterasi TSA
    for it in range(iterations):
        new_population = []

        for i in range(population_size):
            current = population[i].copy()
            new_sol = current.copy()

            # TSA Movement Core (sederhana & kompatibel utk assignment diskrit)
            for t_id in task_ids:
                if random.random() < 0.7:
                    new_sol[t_id] = best_solution[t_id]
                else:
                    new_sol[t_id] = random.choice(vm_names)

            # Gunakan RF untuk memprediksi cost
            encoded = encode_solution(new_sol, vm_names, task_ids)
            predicted_cost = rf.predict([encoded])[0]

            # Evaluasi sebenarnya
            real_cost = calculate_estimated_makespan(new_sol, tasks_dict, vms_dict)

            # Seleksi
            if real_cost < costs[i]:
                population[i] = new_sol
                costs[i] = real_cost

        # Update global best
        new_best_index = np.argmin(costs)
        if costs[new_best_index] < best_cost:
            best_cost = costs[new_best_index]
            best_solution = population[new_best_index]
            print(f"[Iterasi {it}] Better Makespan: {best_cost:.2f}")

        # Retrain RF untuk iterasi berikutnya
        sample_vectors = [encode_solution(population[j], vm_names, task_ids) for j in range(population_size)]
        rf = build_rf_model(sample_vectors, costs)

    print(f"TSA-RF selesai. Best Makespan: {best_cost:.2f}")
    return best_solution
