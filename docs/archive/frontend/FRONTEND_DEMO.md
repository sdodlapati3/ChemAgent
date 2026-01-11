# 🧪 ChemAgent Frontend Demo - Live Now!

## 🌐 **Access the UI**

The ChemAgent web interface is now running at:

```
http://hpcslurm-slurm-login-001:7860
```

Or if you're on the same machine:
```
http://localhost:7860
```

**Process ID:** 520744 (running in background)

---

## 🎨 **What You'll See**

### **Main Interface**

```
╔═══════════════════════════════════════════════════════════════╗
║     🧪 ChemAgent - Pharmaceutical Research Assistant          ║
║                                                                ║
║  Natural language interface for compound lookup, property     ║
║  calculation, similarity search, and target analysis.         ║
╚═══════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────┐
│ Tabs: [🔍 Query] [📦 Batch Processing] [📜 History] [❓ Help] │
└─────────────────────────────────────────────────────────────┘
```

---

## 📍 **Tab 1: 🔍 Query Tab**

### Left Panel - Query Input

```
┌─────────────────────────────────────────────┐
│ Enter your query                            │
│                                             │
│  e.g., What is CHEMBL25? Find similar      │
│       compounds to aspirin.                 │
│                                             │
│ [                                       ]   │
│ [                                       ]   │
│ [                                       ]   │
│                                             │
│  [🚀 Submit]  [🗑️ Clear]                    │
│                                             │
│  ⚙️ Options ▼                               │
│  ☑ Use cache                                │
│  ☐ Verbose output                           │
└─────────────────────────────────────────────┘
```

### Right Panel - Example Queries

```
┌─────────────────────────────────────────────┐
│ 💡 Example Queries                          │
│                                             │
│ [What is CHEMBL25?]                         │
│ [Find similar compounds to aspirin]         │
│ [Get properties for caffeine]               │
│ [What targets does ibuprofen bind to?]      │
│ [Compare molecular weight of aspirin...]    │
└─────────────────────────────────────────────┘
```

### Results Display

```
┌─────────────────────────────────────────────────────────────┐
│ Status                                                       │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ✅ SUCCESS: Query completed in 1.23s                    │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ Results                                                     │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ## Aspirin                                              │ │
│ │                                                         │ │
│ │ **ChEMBL ID:** CHEMBL25                                 │ │
│ │                                                         │ │
│ │ **SMILES:** `CC(=O)Oc1ccccc1C(=O)O`                     │ │
│ │                                                         │ │
│ │ ### Properties                                          │ │
│ │ - **Molecular Weight:** 180.16 Da                       │ │
│ │ - **ALogP:** 1.19                                       │ │
│ │ - **Polar Surface Area:** 63.60 Ų                       │ │
│ │ - **Formula:** C9H8O4                                   │ │
│ │                                                         │ │
│ │ ### Synonyms                                            │ │
│ │ Acetylsalicylic acid, Aspirin, ASA, ...                │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ Visualization                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ [Molecule visualization would appear here]              │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 📍 **Tab 2: 📦 Batch Processing**

```
┌─────────────────────────────────────────────────────────────┐
│ Process multiple queries at once (one per line).            │
│ Queries will be processed in parallel for better            │
│ performance.                                                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Queries (one per line)                                      │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ What is CHEMBL25?                                     │   │
│ │ Find similar compounds to aspirin                     │   │
│ │ Get properties for caffeine                           │   │
│ │                                                       │   │
│ │                                                       │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                             │
│ [🚀 Process Batch]                                          │
│ ☑ Use cache    ☑ Enable parallel                           │
│                                                             │
│ Status:                                                     │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ ✅ Processed 3 queries in 4.56s                       │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                             │
│ Batch Results:                                              │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ ════════════════════════════════════════════════      │   │
│ │ BATCH PROCESSING RESULTS                              │   │
│ │ ════════════════════════════════════════════════      │   │
│ │ Total queries: 3                                      │   │
│ │ Successful: 3                                         │   │
│ │ Failed: 0                                             │   │
│ │ Total time: 4.56s                                     │   │
│ │ Average time: 1.52s per query                         │   │
│ │                                                       │   │
│ │ [1] What is CHEMBL25?                                 │   │
│ │     Status: ✓ Success                                 │   │
│ │     Result: ## Aspirin...                             │   │
│ │                                                       │   │
│ │ [2] Find similar compounds to aspirin                 │   │
│ │     Status: ✓ Success                                 │   │
│ │     Result: Found 10 similar compounds...             │   │
│ │                                                       │   │
│ │ [3] Get properties for caffeine                       │   │
│ │     Status: ✓ Success                                 │   │
│ │     Result: Molecular Weight: 194.19 Da...            │   │
│ └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📍 **Tab 3: 📜 History**

```
┌─────────────────────────────────────────────────────────────┐
│ Search history:  [                    ]                     │
│ [⭐ Show Favorites]  [🗑️ Clear History]                     │
│                                                             │
│ Query History:                                              │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ [                                                     │   │
│ │   {                                                   │   │
│ │     "id": "abc-123",                                  │   │
│ │     "query": "What is CHEMBL25?",                     │   │
│ │     "timestamp": "2026-01-11T15:30:00",               │   │
│ │     "execution_time": 1.23,                           │   │
│ │     "cached": false,                                  │   │
│ │     "favorite": false                                 │   │
│ │   },                                                  │   │
│ │   {                                                   │   │
│ │     "id": "def-456",                                  │   │
│ │     "query": "Calculate properties of CCO",           │   │
│ │     "timestamp": "2026-01-11T15:28:00",               │   │
│ │     "execution_time": 0.89,                           │   │
│ │     "cached": true,                                   │   │
│ │     "favorite": true                                  │   │
│ │   }                                                   │   │
│ │ ]                                                     │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                             │
│ Load from History:                                          │
│ [📥 Load Selected]  [⭐ Toggle Favorite]                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📍 **Tab 4: ❓ Help**

```
┌─────────────────────────────────────────────────────────────┐
│ ## How to Use ChemAgent                                     │
│                                                             │
│ ### Query Types                                             │
│                                                             │
│ 1. **Compound Lookup**                                      │
│    - `What is CHEMBL25?`                                    │
│    - `Tell me about aspirin`                                │
│    - `Look up CC(=O)OC1=CC=CC=C1C(=O)O`                     │
│                                                             │
│ 2. **Property Queries**                                     │
│    - `What is the molecular weight of aspirin?`             │
│    - `Get properties for CHEMBL25`                          │
│    - `Calculate druglikeness for caffeine`                  │
│                                                             │
│ 3. **Similarity Search**                                    │
│    - `Find similar compounds to aspirin`                    │
│    - `Search for analogs of CHEMBL25 with similarity > 0.8` │
│    - `Top 10 most similar compounds to caffeine`            │
│                                                             │
│ 4. **Target Queries**                                       │
│    - `What targets does aspirin bind to?`                   │
│    - `Find compounds that bind to COX-2`                    │
│    - `Get binding affinities for metformin`                 │
│                                                             │
│ 5. **Complex Workflows**                                    │
│    - `Find similar compounds to aspirin and get targets`    │
│    - `Compare properties of aspirin and ibuprofen`          │
│    - `Find COX-2 inhibitors with IC50 < 100nM`              │
│                                                             │
│ ### Features                                                │
│                                                             │
│ - **Caching**: Results cached for faster repeated queries  │
│ - **Parallel Execution**: Independent steps run in parallel│
│ - **Batch Processing**: Process multiple queries           │
│ - **History**: All queries saved for later reference       │
│ - **Favorites**: Mark important queries for quick access   │
│                                                             │
│ ### API Access                                              │
│                                                             │
│ ```bash                                                     │
│ # Single query                                              │
│ curl -X POST http://localhost:8000/query \                 │
│   -H "Content-Type: application/json" \                    │
│   -d '{"query": "What is CHEMBL25?"}'                       │
│ ```                                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎬 **Try These Example Queries**

### 1. Basic Compound Lookup
```
What is CHEMBL25?
```
**Expected Result:** Complete information about Aspirin including structure, properties, synonyms

### 2. Property Calculation
```
Calculate properties of CCO
```
**Expected Result:** Molecular weight, LogP, H-bond donors/acceptors, PSA, etc.

### 3. Similarity Search
```
Find compounds similar to aspirin
```
**Expected Result:** List of similar compounds with Tanimoto similarity scores

### 4. Lipinski Rules
```
Check Lipinski rules for CCO
```
**Expected Result:** Pass/fail status with detailed parameter breakdown

### 5. Complex Query
```
Find compounds similar to CC(=O)Oc1ccccc1C(=O)O and calculate their properties
```
**Expected Result:** Multi-step workflow with similarity search + property calculations

---

## 🎨 **UI Theme & Design**

- **Color Scheme**: Soft, professional (Gradio default theme)
- **Typography**: Clear, readable fonts
- **Layout**: Responsive 2-column design
- **Status Messages**: Color-coded (green=success, red=error, blue=info)
- **Results**: Beautiful markdown rendering
- **Visualizations**: HTML-based compound information

---

## ⌨️ **Keyboard Shortcuts**

- **Ctrl + Enter**: Submit query (in query box)
- **Ctrl + L**: Clear input (when focused)

---

## 🛑 **To Stop the Server**

```bash
# Find the process
ps aux | grep "chemagent.ui.run"

# Kill it
kill 520744

# Or
pkill -f "chemagent.ui.run"
```

---

## 📊 **Performance**

- **First Query**: ~1-3 seconds (API calls)
- **Cached Query**: ~50-100ms (disk cache hit)
- **Batch Processing**: 2-5x speedup with parallel execution
- **Memory Usage**: ~200-500MB (including dependencies)

---

## 🎉 **Enjoy Exploring!**

The ChemAgent UI provides an intuitive, beautiful interface for pharmaceutical research. Try different query types and explore the features!

**Happy researching!** 🧪✨
