#!/usr/bin/env python3
"""
RHCP Chatbot Performance Testing Script

This script benchmarks the chatbot's performance by testing response times,
accuracy, and throughput with various types of queries.
"""

import asyncio
import time
import statistics
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Any, Tuple
from app.chatbot.initializer import initialize_chatbot
from app.chatbot.processor import ChatbotProcessor


class PerformanceTester:
    def __init__(self):
        self.chatbot_processor = None
        self.test_results = []
        
    async def initialize(self):
        """Initialize the chatbot for testing."""
        print("Initializing chatbot for performance testing...")
        self.chatbot_processor = await initialize_chatbot()
        print("✅ Chatbot initialized successfully!")
    
    def load_test_queries(self) -> List[Dict[str, Any]]:
        """Load test queries with expected intents."""
        return [
            # Greetings
            {"query": "Hello", "expected_intent": "greetings.hello", "category": "greetings"},
            {"query": "Hi there", "expected_intent": "greetings.hello", "category": "greetings"},
            {"query": "Goodbye", "expected_intent": "greetings.bye", "category": "greetings"},
            
            # Band members
            {"query": "Who are the band members?", "expected_intent": "band.members", "category": "band_info"},
            {"query": "Tell me about Anthony Kiedis", "expected_intent": "member.biography", "category": "band_info"},
            {"query": "What about Flea?", "expected_intent": "member.biography", "category": "band_info"},
            {"query": "Who is John Frusciante?", "expected_intent": "member.biography", "category": "band_info"},
            {"query": "Tell me about Chad Smith", "expected_intent": "member.biography", "category": "band_info"},
            
            # Albums
            {"query": "What albums do they have?", "expected_intent": "album.info", "category": "albums"},
            {"query": "Tell me about Blood Sugar Sex Magik", "expected_intent": "album.specific", "category": "albums"},
            {"query": "What about Californication?", "expected_intent": "album.specific", "category": "albums"},
            {"query": "Tell me about By the Way", "expected_intent": "album.specific", "category": "albums"},
            
            # Songs
            {"query": "What are their popular songs?", "expected_intent": "song.info", "category": "songs"},
            {"query": "Tell me about Under the Bridge", "expected_intent": "song.specific", "category": "songs"},
            {"query": "What about Californication?", "expected_intent": "song.specific", "category": "songs"},
            {"query": "Tell me about Scar Tissue", "expected_intent": "song.specific", "category": "songs"},
            
            # Band history
            {"query": "When was RHCP formed?", "expected_intent": "band.history", "category": "band_info"},
            {"query": "What's the band's history?", "expected_intent": "band.history", "category": "band_info"},
            
            # Out of scope
            {"query": "What is quantum physics?", "expected_intent": "intent.outofscope", "category": "out_of_scope"},
            {"query": "How to cook pasta?", "expected_intent": "intent.outofscope", "category": "out_of_scope"},
            
            # Edge cases
            {"query": "", "expected_intent": "unrecognized", "category": "edge_cases"},
            {"query": "   ", "expected_intent": "unrecognized", "category": "edge_cases"},
            {"query": "a" * 1000, "expected_intent": "unrecognized", "category": "edge_cases"},
        ]
    
    def test_single_query(self, query: str, expected_intent: str) -> Dict[str, Any]:
        """Test a single query and measure performance."""
        start_time = time.time()
        
        try:
            response = self.chatbot_processor.process_message(query)
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            # Check accuracy
            intent_correct = response.get("intent") == expected_intent
            confidence = response.get("confidence", 0)
            
            return {
                "query": query,
                "expected_intent": expected_intent,
                "actual_intent": response.get("intent"),
                "intent_correct": intent_correct,
                "confidence": confidence,
                "response_time_ms": response_time,
                "response_length": len(response.get("message", "")),
                "entities_count": len(response.get("entities", [])),
                "success": True
            }
            
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            return {
                "query": query,
                "expected_intent": expected_intent,
                "actual_intent": None,
                "intent_correct": False,
                "confidence": 0,
                "response_time_ms": response_time,
                "response_length": 0,
                "entities_count": 0,
                "success": False,
                "error": str(e)
            }
    
    def run_performance_test(self, num_iterations: int = 5) -> Dict[str, Any]:
        """Run comprehensive performance test."""
        print(f"Running performance test with {num_iterations} iterations per query...")
        
        test_queries = self.load_test_queries()
        all_results = []
        
        for i in range(num_iterations):
            print(f"Iteration {i + 1}/{num_iterations}")
            
            for test_case in test_queries:
                result = self.test_single_query(test_case["query"], test_case["expected_intent"])
                result["category"] = test_case["category"]
                result["iteration"] = i + 1
                all_results.append(result)
        
        return self.analyze_results(all_results, test_queries)
    
    def analyze_results(self, all_results: List[Dict], test_queries: List[Dict]) -> Dict[str, Any]:
        """Analyze test results and generate statistics."""
        # Group results by query
        query_results = {}
        for result in all_results:
            query = result["query"]
            if query not in query_results:
                query_results[query] = []
            query_results[query].append(result)
        
        # Calculate statistics for each query
        query_stats = {}
        for query, results in query_results.items():
            response_times = [r["response_time_ms"] for r in results if r["success"]]
            confidences = [r["confidence"] for r in results if r["success"]]
            success_rate = sum(1 for r in results if r["success"]) / len(results)
            accuracy = sum(1 for r in results if r["intent_correct"]) / len(results)
            
            query_stats[query] = {
                "avg_response_time_ms": statistics.mean(response_times) if response_times else 0,
                "min_response_time_ms": min(response_times) if response_times else 0,
                "max_response_time_ms": max(response_times) if response_times else 0,
                "std_response_time_ms": statistics.stdev(response_times) if len(response_times) > 1 else 0,
                "avg_confidence": statistics.mean(confidences) if confidences else 0,
                "success_rate": success_rate,
                "accuracy": accuracy,
                "total_tests": len(results)
            }
        
        # Calculate overall statistics
        all_response_times = [r["response_time_ms"] for r in all_results if r["success"]]
        all_confidences = [r["confidence"] for r in all_results if r["success"]]
        overall_success_rate = sum(1 for r in all_results if r["success"]) / len(all_results)
        overall_accuracy = sum(1 for r in all_results if r["intent_correct"]) / len(all_results)
        
        # Category-wise statistics
        category_stats = {}
        for test_case in test_queries:
            category = test_case["category"]
            if category not in category_stats:
                category_stats[category] = {"queries": [], "results": []}
            category_stats[category]["queries"].append(test_case["query"])
        
        for result in all_results:
            category = result["category"]
            if category in category_stats:
                category_stats[category]["results"].append(result)
        
        for category, data in category_stats.items():
            results = data["results"]
            response_times = [r["response_time_ms"] for r in results if r["success"]]
            accuracies = [r["intent_correct"] for r in results]
            
            category_stats[category] = {
                "avg_response_time_ms": statistics.mean(response_times) if response_times else 0,
                "accuracy": sum(accuracies) / len(accuracies) if accuracies else 0,
                "total_queries": len(data["queries"]),
                "total_tests": len(results)
            }
        
        return {
            "overall_stats": {
                "total_queries": len(test_queries),
                "total_tests": len(all_results),
                "avg_response_time_ms": statistics.mean(all_response_times) if all_response_times else 0,
                "min_response_time_ms": min(all_response_times) if all_response_times else 0,
                "max_response_time_ms": max(all_response_times) if all_response_times else 0,
                "std_response_time_ms": statistics.stdev(all_response_times) if len(all_response_times) > 1 else 0,
                "avg_confidence": statistics.mean(all_confidences) if all_confidences else 0,
                "overall_success_rate": overall_success_rate,
                "overall_accuracy": overall_accuracy
            },
            "query_stats": query_stats,
            "category_stats": category_stats,
            "raw_results": all_results
        }
    
    def print_results(self, results: Dict[str, Any]):
        """Print formatted test results."""
        overall = results["overall_stats"]
        category_stats = results["category_stats"]
        
        print("\n" + "="*60)
        print("🎸 RHCP CHATBOT PERFORMANCE TEST RESULTS")
        print("="*60)
        
        print(f"\n📊 OVERALL STATISTICS:")
        print(f"   Total Queries Tested: {overall['total_queries']}")
        print(f"   Total Tests Run: {overall['total_tests']}")
        print(f"   Success Rate: {overall['overall_success_rate']:.2%}")
        print(f"   Accuracy: {overall['overall_accuracy']:.2%}")
        print(f"   Average Response Time: {overall['avg_response_time_ms']:.2f} ms")
        print(f"   Min Response Time: {overall['min_response_time_ms']:.2f} ms")
        print(f"   Max Response Time: {overall['max_response_time_ms']:.2f} ms")
        print(f"   Response Time Std Dev: {overall['std_response_time_ms']:.2f} ms")
        print(f"   Average Confidence: {overall['avg_confidence']:.3f}")
        
        print(f"\n📈 CATEGORY-WISE PERFORMANCE:")
        for category, stats in category_stats.items():
            print(f"   {category.upper()}:")
            print(f"     - Avg Response Time: {stats['avg_response_time_ms']:.2f} ms")
            print(f"     - Accuracy: {stats['accuracy']:.2%}")
            print(f"     - Queries: {stats['total_queries']}")
        
        print(f"\n🏆 TOP PERFORMING QUERIES:")
        query_stats = results["query_stats"]
        sorted_queries = sorted(
            query_stats.items(), 
            key=lambda x: x[1]["avg_response_time_ms"]
        )[:5]
        
        for query, stats in sorted_queries:
            print(f"   '{query[:50]}{'...' if len(query) > 50 else ''}':")
            print(f"     - Response Time: {stats['avg_response_time_ms']:.2f} ms")
            print(f"     - Accuracy: {stats['accuracy']:.2%}")
        
        print(f"\n🐌 SLOWEST QUERIES:")
        sorted_queries_slow = sorted(
            query_stats.items(), 
            key=lambda x: x[1]["avg_response_time_ms"], 
            reverse=True
        )[:5]
        
        for query, stats in sorted_queries_slow:
            print(f"   '{query[:50]}{'...' if len(query) > 50 else ''}':")
            print(f"     - Response Time: {stats['avg_response_time_ms']:.2f} ms")
            print(f"     - Accuracy: {stats['accuracy']:.2%}")
        
        print("\n" + "="*60)
    
    def save_results(self, results: Dict[str, Any], filename: str = "performance_results.json"):
        """Save test results to JSON file."""
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"📁 Results saved to {filename}")


async def main():
    """Main function to run performance tests."""
    tester = PerformanceTester()
    await tester.initialize()
    
    # Run performance test
    results = tester.run_performance_test(num_iterations=3)
    
    # Print and save results
    tester.print_results(results)
    tester.save_results(results)


if __name__ == "__main__":
    asyncio.run(main()) 