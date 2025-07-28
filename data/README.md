# Data Directory Structure

This directory contains all data files for the RHCP Chatbot project, organized by type and purpose.

## Directory Structure

```
data/
├── raw/           # Raw, unprocessed data files
│   ├── band-info.json
│   └── discography.json
├── processed/     # Processed and cleaned data files
│   ├── base-corpus.json
│   └── rhcp-corpus.json
├── models/        # Trained model files
│   ├── logistic_regression_classifier.joblib
│   └── logistic_regression_classifier.json
├── results/       # Performance results and analysis
│   └── performance_results.json
└── backups/       # Backup versions of data files
    ├── backup_20250727_205130/
    └── backup_20250727_211812/
```

## Data Types

### Raw Data (`raw/`)
- **band-info.json**: Basic information about the Red Hot Chili Peppers
- **discography.json**: Complete discography with album and song information

### Processed Data (`processed/`)
- **base-corpus.json**: Base training corpus for the chatbot
- **rhcp-corpus.json**: RHCP-specific training corpus

### Models (`models/`)
- **logistic_regression_classifier.joblib**: Trained logistic regression model
- **logistic_regression_classifier.json**: Model metadata and configuration

### Results (`results/`)
- **performance_results.json**: Model performance metrics and evaluation results

### Backups (`backups/`)
- Historical versions of data files for version control and rollback purposes

## Usage Guidelines

1. **Raw data** should never be modified directly - create processed versions instead
2. **Processed data** can be updated as needed, but maintain backups
3. **Models** should be versioned and documented
4. **Results** should be timestamped and include evaluation metrics
5. **Backups** should be created before major data changes

## Data Pipeline

```
Raw Data → Processing → Training Corpus → Model Training → Performance Evaluation
    ↓           ↓              ↓              ↓                ↓
  raw/      processed/     processed/      models/         results/
``` 