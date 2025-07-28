# RHCP Chatbot ML Pipeline - Refactored

A professional, modular, and configurable machine learning pipeline for training the RHCP Chatbot intent classification model.

## 🎯 Key Features

### ✅ **Professional ML Structure**
- **Configuration Management**: YAML-based settings for all components
- **Modular Design**: Reusable, independent components  
- **Comprehensive Logging**: Structured logging across all modules
- **Data Pipeline**: Organized data flow from raw to processed to results
- **Automated Evaluation**: Confusion matrices, cross-validation, and reports

### ✅ **Industry Best Practices**
- **Reproducible**: Fixed random seeds and versioning
- **Scalable**: Easy to add new features and models
- **Maintainable**: Clean separation of concerns
- **Configurable**: Easy experimentation with different settings
- **Documented**: Comprehensive documentation and examples

## 📁 Project Structure

```
rhcp-chatbot/
├── config/                           # Configuration Management
│   ├── training_config.yaml          # Training parameters & settings
│   └── data_config.yaml              # Data processing configuration
│
├── data/                             # Organized Data Structure  
│   ├── raw/                          # Raw, unprocessed data
│   ├── processed/                    # Cleaned training data
│   ├── models/                       # Trained model artifacts
│   ├── results/                      # Evaluation results & reports
│   ├── backups/                      # Versioned data backups
│   └── README.md                     # Data documentation
│
├── scripts/                          # Modular ML Pipeline
│   ├── utils/                        # Core utilities
│   │   ├── config_manager.py         # Configuration loading
│   │   ├── logger_setup.py           # Logging utilities
│   │   ├── data_utils.py             # Data processing utilities
│   │   └── model_utils.py            # Model training utilities
│   │
│   ├── data/                         # Data Processing
│   │   ├── load_data.py              # Data loading & analysis
│   │   ├── validate_data.py          # Data validation
│   │   └── enhance_data.py           # Minority class enhancement
│   │
│   ├── training/                     # Model Training
│   │   └── train_model.py            # Main training pipeline
│   │
│   └── evaluation/                   # Model Evaluation
│       └── evaluate_model.py         # Comprehensive evaluation
│
├── notebooks/                        # Interactive Development
│   ├── model_training_refactored.ipynb  # New modular notebook
│   └── model_training.ipynb          # Original notebook (preserved)
│
├── logs/                             # Application Logs
│   ├── training.log                  # Training pipeline logs
│   ├── data_processing.log           # Data processing logs
│   └── evaluation.log               # Evaluation logs
│
├── requirements_ml.txt               # ML-specific dependencies
└── ML_PIPELINE_README.md            # This file
```

## 🚀 Quick Start

### 1. **Installation**

```bash
# Install dependencies
pip install -r requirements_ml.txt

# Download NLTK data (if not already present)
python -c "import nltk; nltk.download('punkt')"
```

### 2. **Configuration**

The pipeline is driven by YAML configuration files:

**`config/training_config.yaml`** - Main training settings
**`config/data_config.yaml`** - Data processing settings

Modify these files to experiment with different settings.

### 3. **Run Training Pipeline**

**Option A: Command Line (Recommended)**
```bash
python scripts/training/train_model.py
```

**Option B: Interactive Jupyter Notebook**
```bash
jupyter notebook notebooks/model_training_refactored.ipynb
```

**Option C: Individual Components**
```bash
# Data loading and analysis
python scripts/data/load_data.py

# Data validation
python scripts/data/validate_data.py

# Data enhancement
python scripts/data/enhance_data.py

# Model evaluation
python scripts/evaluation/evaluate_model.py
```

## 📊 Pipeline Workflow

### 1. **Data Loading** (`scripts/data/load_data.py`)
- Loads training data from configured JSON corpus files
- Analyzes class distribution and balance
- Creates data backups
- Validates data integrity

### 2. **Data Enhancement** (`scripts/data/enhance_data.py`) [Optional]
- Identifies minority classes based on thresholds
- Adds template-based examples for underrepresented intents
- Updates source corpus files
- Analyzes enhancement impact

### 3. **Model Training** (`scripts/training/train_model.py`)
- Creates TF-IDF + Logistic Regression pipeline
- Trains model with class balancing
- Implements cross-validation
- Tests on specific cases
- Saves model with metadata

### 4. **Model Evaluation** (`scripts/evaluation/evaluate_model.py`)
- Generates confusion matrices
- Creates performance visualizations
- Analyzes feature importance
- Compares test vs CV performance
- Provides improvement recommendations

## ⚙️ Configuration Options

### Training Configuration (`config/training_config.yaml`)

```yaml
# Model settings
model:
  type: "LogisticRegression"
  vectorizer:
    ngram_range: [1, 3]
    stop_words: "english"
  classifier:
    class_weight: "balanced"
    multi_class: "multinomial"

# Training parameters
training:
  test_size: 0.2
  cv_folds: 5
  stratify: true

# Enhancement settings
enhancement:
  enable_minority_class_enhancement: true
  minority_threshold_percentage: 2.0
```

### Data Configuration (`config/data_config.yaml`)

```yaml
# Data paths
paths:
  processed: "data/processed"
  models: "data/models"
  results: "data/results"

# Validation rules
validation:
  required_fields: ["intent", "utterances"]
  utterance_rules:
    min_length: 3
    min_per_intent: 5
```

## 📈 Performance & Results

### Automated Outputs

The pipeline automatically generates:

1. **Trained Model**: `data/models/logistic_regression_classifier.joblib`
2. **Model Metadata**: `data/models/logistic_regression_classifier.json`
3. **Training Results**: `data/results/training_results.json`
4. **Confusion Matrix**: `data/results/confusion_matrix.png`
5. **Performance Plots**: `data/results/cv_performance.png`
6. **Detailed Analysis**: `data/results/model_analysis.json`
7. **Logs**: `logs/training.log`

### Key Metrics Tracked

- **Accuracy**: Overall classification accuracy
- **Macro F1**: Average F1 across all classes (handles imbalance)
- **Weighted F1**: F1 weighted by class support
- **Cross-Validation**: 5-fold CV with confidence intervals
- **Class-specific**: Precision, recall, F1 for each intent

## 🔧 Advanced Usage

### Custom Model Training

```python
from scripts.utils.config_manager import ConfigManager
from scripts.training.train_model import ModelTrainer

# Initialize with custom config
config_manager = ConfigManager()
trainer = ModelTrainer()

# Run training pipeline
pipeline, test_results, cv_results = trainer.run_training_pipeline()
```

### Data Enhancement

```python
from scripts.data.enhance_data import DataEnhancer
from scripts.data.load_data import DataLoader

# Load and enhance data
loader = DataLoader()
enhancer = DataEnhancer()

df = loader.load_training_data()
enhanced_df = enhancer.enhance_minority_classes(df)
```

### Custom Evaluation

```python
from scripts.evaluation.evaluate_model import ModelEvaluator

evaluator = ModelEvaluator()
evaluator.generate_evaluation_report(
    pipeline, X_test, y_test, test_results, cv_results
)
```

## 🛠️ Development & Extension

### Adding New Features

1. **New Model Type**: Add to `scripts/utils/model_utils.py`
2. **New Data Source**: Extend `scripts/data/load_data.py`  
3. **New Evaluation Metric**: Add to `scripts/evaluation/evaluate_model.py`
4. **New Configuration**: Update YAML files in `config/`

### Logging

All components use structured logging:

```python
from scripts.utils.logger_setup import setup_logger

logger = setup_logger("my_component", "logs/my_component.log")
logger.info("Processing started...")
```

### Configuration Management

```python
from scripts.utils.config_manager import ConfigManager

config_manager = ConfigManager()
training_config = config_manager.get_training_config()
value = config_manager.get_nested_value("training_config", "model.type")
```

## 📊 Comparison: Before vs After

### Before (Original Notebook)
❌ Single monolithic notebook  
❌ Hard-coded parameters  
❌ No configuration management  
❌ Limited reusability  
❌ Manual execution steps  
❌ Scattered outputs  

### After (Refactored Pipeline)
✅ Modular, reusable components  
✅ YAML-based configuration  
✅ Professional project structure  
✅ Automated pipeline execution  
✅ Comprehensive logging & evaluation  
✅ Industry best practices  

## 🎯 Benefits

### For Development
- **Faster Experimentation**: Change configs instead of code
- **Better Debugging**: Structured logging and modular components
- **Code Reusability**: Components can be used independently
- **Maintainability**: Clear separation of concerns

### For Production
- **Reproducibility**: Fixed seeds and versioning
- **Monitoring**: Comprehensive logging and metrics
- **Scalability**: Easy to extend and modify
- **Reliability**: Automated validation and error handling

### For Collaboration
- **Documentation**: Self-documenting code and configs
- **Standards**: Consistent structure and practices
- **Onboarding**: Clear entry points and examples
- **Version Control**: Proper artifact management

## 🏆 Key Improvements Over Original

1. **Fixed Deprecation Warnings**: Updated to use `multi_class='multinomial'`
2. **Proper Class Balancing**: Automatic minority class enhancement
3. **Configuration Management**: YAML-based settings for easy experimentation
4. **Comprehensive Evaluation**: Confusion matrices, CV analysis, recommendations
5. **Professional Structure**: Industry-standard ML project organization
6. **Automated Workflows**: End-to-end pipeline execution
7. **Better Data Management**: Organized data paths and versioning
8. **Enhanced Logging**: Structured logging across all components

## 📝 License & Contributing

This refactored ML pipeline maintains compatibility with the original RHCP Chatbot project while providing a professional, scalable foundation for machine learning development.

For questions or contributions, follow the same process as the main project. 