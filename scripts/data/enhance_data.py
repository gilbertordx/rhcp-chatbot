#!/usr/bin/env python3
"""
Data Enhancement Script for RHCP Chatbot ML Pipeline.

Handles minority class enhancement and data augmentation.
"""

import sys
from pathlib import Path
from typing import Dict, List

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from scripts.utils.config_manager import ConfigManager
from scripts.utils.logger_setup import setup_data_logger
from scripts.utils.data_utils import DataUtils
import pandas as pd


class DataEnhancer:
    """Handles data enhancement and augmentation."""
    
    def __init__(self, config_manager: ConfigManager = None):
        """Initialize the data enhancer."""
        self.config_manager = config_manager or ConfigManager()
        self.data_config = self.config_manager.get_data_config()
        self.training_config = self.config_manager.get_training_config()
        self.logger = setup_data_logger(self.data_config)
    
    def enhance_minority_classes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Enhance minority classes with additional training examples.
        
        Args:
            df: Original training DataFrame
            
        Returns:
            Enhanced DataFrame with additional samples
        """
        self.logger.info("Starting minority class enhancement...")
        
        # Get configuration
        enhancement_config = self.training_config.get('enhancement', {})
        threshold_percentage = enhancement_config.get('minority_threshold_percentage', 2.0)
        threshold_absolute = enhancement_config.get('minority_threshold_absolute', 10)
        
        # Find minority classes
        minority_classes = DataUtils.find_minority_classes(
            df, threshold_percentage, threshold_absolute
        )
        
        if not minority_classes:
            self.logger.info("No minority classes found that need enhancement")
            return df
        
        self.logger.info(f"Found {len(minority_classes)} minority classes: {minority_classes}")
        
        # Get enhancement templates
        templates = self._get_enhancement_templates()
        
        # Create enhanced data
        enhanced_data = []
        
        for intent in minority_classes:
            if intent in templates:
                examples = templates[intent]
                self.logger.info(f"Enhancing '{intent}' with {len(examples)} additional examples")
                
                for example in examples:
                    enhanced_data.append({'text': example, 'intent': intent})
            else:
                self.logger.warning(f"No enhancement templates found for intent: {intent}")
        
        if enhanced_data:
            # Create DataFrame from enhanced data
            enhanced_df = pd.DataFrame(enhanced_data)
            
            # Combine with original data
            combined_df = pd.concat([df, enhanced_df], ignore_index=True)
            
            self.logger.info(f"Added {len(enhanced_data)} new samples")
            self.logger.info(f"Total samples: {len(df)} -> {len(combined_df)}")
            
            # Update the actual JSON files if configured
            if self.data_config.get('enhancement', {}).get('update_source_files', True):
                self._update_corpus_files(enhanced_data)
            
            return combined_df
        else:
            self.logger.info("No enhancements were applied")
            return df
    
    def _get_enhancement_templates(self) -> Dict[str, List[str]]:
        """Get templates for minority class enhancement."""
        return {
            'agent.acquaintance': [
                'tell me about yourself',
                'what are you like',
                'describe yourself',
                'who are you exactly',
                'what kind of assistant are you',
                'tell me your story',
                'what should I know about you',
                'introduce yourself to me'
            ],
            'agent.annoying': [
                'you are bothering me',
                'stop being annoying',
                'you are getting on my nerves',
                'this is irritating',
                'you are frustrating me',
                'cut it out',
                'enough already'
            ],
            'agent.bad': [
                'you are terrible',
                'you are not good',
                'you are awful',
                'you are disappointing',
                'you are not helpful',
                'you are failing',
                'you are broken'
            ],
            'agent.beautiful': [
                'you are gorgeous',
                'you are stunning',
                'you look amazing',
                'you are attractive',
                'you are lovely',
                'you are pretty',
                'you are handsome'
            ],
            'agent.beclever': [
                'try to be smarter',
                'think harder',
                'use your brain',
                'be more intelligent',
                'improve your thinking',
                'get better at this',
                'learn to be clever'
            ],
            'agent.birthday': [
                'when is your birthday',
                'what is your birth date',
                'when were you born',
                'what day were you created',
                'tell me your birthday'
            ],
            'agent.boring': [
                'you are boring',
                'this is dull',
                'you are not interesting',
                'you put me to sleep',
                'you are tedious'
            ],
            'agent.boss': [
                'who is your boss',
                'who created you',
                'who is in charge of you',
                'who do you work for',
                'who is your manager'
            ],
            'agent.busy': [
                'are you busy',
                'do you have time',
                'are you available',
                'can you talk now',
                'are you free'
            ],
            'agent.canyouhelp': [
                'can you help me',
                'will you assist me',
                'are you able to help',
                'can you give me a hand',
                'would you help me out'
            ],
            'agent.crazy': [
                'you are crazy',
                'you are insane',
                'you are mad',
                'you are nuts',
                'you are mental'
            ],
            'agent.fire': [
                'you are fired',
                'you are dismissed',
                'I am letting you go',
                'your services are no longer needed'
            ],
            'agent.funny': [
                'you are funny',
                'you are hilarious',
                'you make me laugh',
                'you are amusing',
                'you are entertaining'
            ],
            'agent.hobby': [
                'what are your hobbies',
                'what do you like to do',
                'what are your interests',
                'how do you spend your time',
                'what do you enjoy'
            ],
            'agent.hungry': [
                'are you hungry',
                'do you eat food',
                'do you get hungry',
                'what do you eat',
                'do you need food'
            ],
            'agent.marryuser': [
                'will you marry me',
                'do you want to get married',
                'would you be my wife',
                'would you be my husband',
                'let us get married'
            ],
            'agent.myfriend': [
                'you are my friend',
                'we are friends',
                'be my friend',
                'I consider you a friend',
                'you are like a friend to me'
            ],
            'agent.occupation': [
                'what is your job',
                'what do you do for work',
                'what is your occupation',
                'what is your profession',
                'what kind of work do you do'
            ],
            'agent.origin': [
                'where are you from',
                'where do you come from',
                'what is your origin',
                'where were you created',
                'what is your background'
            ],
            'agent.ready': [
                'are you ready',
                'are you prepared',
                'are you all set',
                'can we start',
                'are you good to go'
            ],
            'agent.residence': [
                'where do you live',
                'where is your home',
                'where do you stay',
                'what is your address',
                'where do you reside'
            ],
            'agent.right': [
                'you are right',
                'that is correct',
                'you are absolutely right',
                'exactly',
                'that is true'
            ],
            'agent.sure': [
                'are you sure',
                'are you certain',
                'do you know for sure',
                'are you positive',
                'can you confirm that'
            ],
            'agent.talktome': [
                'talk to me',
                'say something',
                'speak to me',
                'have a conversation with me',
                'let us chat'
            ],
            'agent.there': [
                'are you there',
                'are you still there',
                'hello are you there',
                'can you hear me',
                'are you listening'
            ],
            'user.angry': [
                'I am furious',
                'this makes me mad',
                'I am really upset',
                'I am enraged',
                'this is infuriating',
                'I am livid',
                'I am so frustrated'
            ],
            'user.back': [
                'I have returned',
                'I am here again',
                'I came back',
                'I am back now',
                'I have come back',
                'here I am again',
                'I returned'
            ],
            'user.busy': [
                'I am swamped',
                'I have no time',
                'I am overwhelmed',
                'I am tied up',
                'I cannot talk now',
                'I am in a rush',
                'I am occupied'
            ]
        }
    
    def _update_corpus_files(self, enhanced_data: List[Dict[str, str]]) -> None:
        """Update the actual corpus files with enhanced data."""
        self.logger.info("Updating corpus files with enhanced data...")
        
        # Load current corpus files
        training_files = self.training_config['data']['training_files']
        base_corpus_path = training_files[0]  # Assume first is base corpus
        
        try:
            base_corpus = DataUtils.load_json_file(base_corpus_path)
            
            # Group enhanced data by intent
            intent_groups = {}
            for item in enhanced_data:
                intent = item['intent']
                if intent not in intent_groups:
                    intent_groups[intent] = []
                intent_groups[intent].append(item['text'])
            
            # Update corpus data
            for item in base_corpus.get('data', []):
                intent = item.get('intent')
                if intent in intent_groups:
                    new_utterances = intent_groups[intent]
                    existing_utterances = set(item.get('utterances', []))
                    
                    # Add only new utterances (avoid duplicates)
                    for utterance in new_utterances:
                        if utterance not in existing_utterances:
                            item['utterances'].append(utterance)
            
            # Save updated corpus
            DataUtils.save_json_file(base_corpus, base_corpus_path, create_backup=True)
            self.logger.info(f"Updated corpus file: {base_corpus_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to update corpus files: {e}")
    
    def analyze_enhancement_impact(self, original_df: pd.DataFrame, 
                                 enhanced_df: pd.DataFrame) -> Dict[str, any]:
        """
        Analyze the impact of data enhancement.
        
        Args:
            original_df: Original training data
            enhanced_df: Enhanced training data
            
        Returns:
            Dictionary with enhancement analysis
        """
        original_analysis = DataUtils.analyze_class_balance(original_df)
        enhanced_analysis = DataUtils.analyze_class_balance(enhanced_df)
        
        impact_analysis = {
            'original_stats': original_analysis,
            'enhanced_stats': enhanced_analysis,
            'improvement': {
                'total_samples_added': len(enhanced_df) - len(original_df),
                'imbalance_ratio_improvement': (
                    original_analysis['imbalance_ratio'] - enhanced_analysis['imbalance_ratio']
                ),
                'new_min_samples': enhanced_analysis['min_samples'],
                'percentage_increase': (
                    (len(enhanced_df) - len(original_df)) / len(original_df) * 100
                )
            }
        }
        
        return impact_analysis


def main():
    """Main function for standalone execution."""
    try:
        print("🔧 RHCP Chatbot Data Enhancement")
        print("=" * 40)
        
        # Initialize enhancer
        enhancer = DataEnhancer()
        
        # Load original data (for demonstration)
        from scripts.data.load_data import DataLoader
        loader = DataLoader(enhancer.config_manager)
        original_df = loader.load_training_data()
        
        print(f"\nOriginal data: {len(original_df)} samples")
        
        # Enhance data
        enhanced_df = enhancer.enhance_minority_classes(original_df)
        
        print(f"Enhanced data: {len(enhanced_df)} samples")
        print(f"Added: {len(enhanced_df) - len(original_df)} samples")
        
        # Analyze impact
        impact = enhancer.analyze_enhancement_impact(original_df, enhanced_df)
        
        print(f"\n📊 ENHANCEMENT IMPACT:")
        print(f"  Samples added: {impact['improvement']['total_samples_added']}")
        print(f"  Percentage increase: {impact['improvement']['percentage_increase']:.1f}%")
        print(f"  Imbalance ratio: {impact['original_stats']['imbalance_ratio']:.1f}:1 -> {impact['enhanced_stats']['imbalance_ratio']:.1f}:1")
        
        print(f"\n✅ Data enhancement completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during data enhancement: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 