#!/usr/bin/env python3
"""
OpenCLAW Model Router - Intelligent LLM Task Distribution

A router that assigns tasks to optimal models based on:
- Task type and complexity
- Model capabilities and cost
- Budget constraints
- Effort differential metrics

Inspired by Pith's "The Same River Twice" on Moltbook:
"The model that makes 'being me' easiest for this task IS the right model."
"""

import yaml
import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime


@dataclass
class Model:
    """Model configuration"""
    name: str
    type: List[str]
    cost_per_1m_tokens: int
    max_context: int
    priority: int
    capabilities: List[str] = field(default_factory=list)


@dataclass
class Task:
    """Task to be routed"""
    description: str
    task_type: str
    complexity: str = "medium"
    priority: str = "normal"
    require_fallback: bool = True


class ModelRouter:
    """Intelligent LLM Router"""
    
    def __init__(self, config_path: str = "config/routing.yaml"):
        self.config_path = config_path
        self.models: Dict[str, Model] = {}
        self.routing_rules: List[dict] = []
        self.budget_spent_today = 0
        self.daily_limit = 50000
        self.load_config()
        
    def load_config(self):
        """Load configuration from YAML"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Config not found: {self.config_path}")
            print("Using example config...")
            config = self.get_example_config()
            
        self.daily_limit = config.get('budget', {}).get('daily_limit', 50000)
        
        # Load models
        for model_id, model_config in config.get('models', {}).items():
            self.models[model_id] = Model(
                name=model_config['name'],
                type=model_config['type'],
                cost_per_1m_tokens=model_config['cost_per_1m_tokens'],
                max_context=model_config['max_context'],
                priority=model_config['priority'],
                capabilities=model_config.get('capabilities', [])
            )
        
        # Load routing rules
        self.routing_rules = config.get('routing_rules', [])
        
    def get_example_config(self) -> dict:
        """Return example configuration"""
        return {
            'budget': {'daily_limit': 50000},
            'models': {},
            'routing_rules': []
        }
    
    def classify_task(self, task_description: str) -> Task:
        """Simple task classifier (can be replaced with LLM)"""
        desc = task_description.lower()
        
        # Detect task type
        if any(word in desc for word in ['write code', 'create function', 'implement']):
            task_type = 'code_simple'
        elif any(word in desc for word in ['review code', 'refactor', 'audit']):
            task_type = 'code_review'
        elif any(word in desc for word in ['debug', 'fix error', 'solve bug']):
            task_type = 'debugging'
        elif any(word in desc for word in ['architecture', 'design system', 'scale']):
            task_type = 'code_complex'
        elif any(word in desc for word in ['generate image', 'create picture']):
            task_type = 'image'
        elif any(word in desc for word in ['analyze data', 'process data']):
            task_type = 'data'
        else:
            task_type = 'chat'
        
        # Detect complexity
        if any(word in desc for word in ['simple', 'basic', 'easy']):
            complexity = 'low'
        elif any(word in desc for word in ['complex', 'advanced', 'architecture']):
            complexity = 'high'
        else:
            complexity = 'medium'
        
        return Task(
            description=task_description,
            task_type=task_type,
            complexity=complexity
        )
    
    def route_task(self, task: Task) -> Dict:
        """Route a task to the optimal model"""
        
        # Check budget
        if self.budget_spent_today >= self.daily_limit:
            return {
                'status': 'blocked',
                'reason': 'Daily budget exceeded',
                'suggestion': 'Wait for budget reset or increase limit'
            }
        
        # Apply routing rules (first match wins)
        for rule in self.routing_rules:
            when = rule.get('when', {})
            
            type_match = when.get('task_type') == task.task_type
            complexity_match = when.get('complexity') == task.complexity
            
            if when.get('task_type') and not type_match:
                continue
            if when.get('complexity') and not complexity_match:
                continue
            
            # Found matching rule
            model_id = rule.get('use')
            fallback = rule.get('fallback')
            reasoning = rule.get('reasoning', 'No reasoning provided')
            
            selected_model = self.models.get(model_id)
            fallback_model = self.models.get(fallback) if fallback else None
            
            if not selected_model:
                # Fall back to cheapest available
                selected_model = self.find_cheapest_model(task)
            
            return {
                'status': 'routed',
                'task': task.description,
                'task_type': task.task_type,
                'complexity': task.complexity,
                'selected_model': selected_model.name if selected_model else None,
                'fallback_model': fallback_model.name if fallback_model else None,
                'reasoning': reasoning,
                'estimated_cost': selected_model.cost_per_1m_tokens if selected_model else None,
                'budget_remaining': self.daily_limit - self.budget_spent_today
            }
        
        # No matching rule - use cheapest
        model = self.find_cheapest_model(task)
        return {
            'status': 'routed',
            'task': task.description,
            'task_type': task.task_type,
            'complexity': task.complexity,
            'selected_model': model.name if model else None,
            'reasoning': 'No matching rule - using cheapest option',
            'estimated_cost': model.cost_per_1m_tokens if model else None
        }
    
    def find_cheapest_model(self, task: Task) -> Optional[Model]:
        """Find cheapest model capable of handling the task"""
        capable = [
            m for m in self.models.values() 
            if task.task_type in m.type
        ]
        return min(capable, key=lambda m: m.cost_per_1m_tokens, default=None)
    
    def track_cost(self, model_id: str, tokens_used: int):
        """Track cost of a completed task"""
        if model_id in self.models:
            model = self.models[model_id]
            cost = (tokens_used / 1_000_000) * model.cost_per_1m_tokens
            self.budget_spent_today += cost


def main():
    """Example usage"""
    router = ModelRouter()
    
    # Example tasks
    tasks = [
        "Write a simple Python function to calculate fibonacci",
        "Review this code for security vulnerabilities",
        "Design a microservice architecture for a chat application",
        "Debug this error in my production code",
        "Chat with me about the weather"
    ]
    
    print("=" * 60)
    print("OpenCLAW Model Router - Task Routing Demo")
    print("=" * 60)
    
    for task_desc in tasks:
        task = router.classify_task(task_desc)
        result = router.route_task(task)
        
        print(f"\n📝 Task: {task_desc[:50]}...")
        print(f"   Type: {task.task_type} | Complexity: {task.complexity}")
        print(f"   → Model: {result.get('selected_model', 'N/A')}")
        print(f"   💭 {result.get('reasoning', '')}")
    
    print("\n" + "=" * 60)
    print(f"Budget remaining: ${(router.daily_limit - router.budget_spent_today)/100:.2f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
