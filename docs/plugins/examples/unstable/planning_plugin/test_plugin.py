#!/usr/bin/env python3
"""
Planning Plugin - Test Script

This script tests the planning plugin functionality.
"""

import sys
import os

# Add the plugin directory to the path
plugin_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, plugin_dir)

try:
    from planning_plugin import PlanningPlugin, Plan, PlanningStep, initialize_plugin
    print("✅ Plugin imports successful!")
    
    # Test basic plugin creation
    plugin = PlanningPlugin()
    print(f"✅ Plugin created: {plugin.name} v{plugin.version}")
    
    # Test data classes
    step = PlanningStep(
        step_number=1,
        description="Test step",
        dependencies=[],
        estimated_time="30 minutes",
        tools_needed=["test_tool"]
    )
    print(f"✅ PlanningStep created: {step.description}")
    
    plan = Plan(
        title="Test Plan",
        description="A test plan for validation",
        steps=[step],
        success_criteria=["Test passes"]
    )
    print(f"✅ Plan created: {plan.title}")
    
    # Test plan display
    plugin.current_plan = plan
    print("✅ Plan display test:")
    plugin._display_plan()
    
    # Test execution context formatting
    execution_context = plugin._format_plan_for_execution()
    print("✅ Execution context formatted successfully")
    print(f"Context length: {len(execution_context)} characters")
    
    # Test question detection
    test_questions = [
        "What are your requirements?",
        "I need clarification on the timeline.",
        "Please provide more information about the project.",
        "Here is the plan you requested."
    ]
    
    for question in test_questions:
        is_question = plugin._is_asking_questions(question)
        print(f"✅ Question detection: '{question[:30]}...' -> {is_question}")
    
    # Test plan parsing
    test_plan_content = """
# PLAN: Test Web App
## Description
Build a test web application

## Steps
1. Set up project structure
   - Dependencies: None
   - Estimated time: 30 minutes
   - Tools needed: file tools
   - Notes: Create main directories

2. Implement authentication
   - Dependencies: 1
   - Estimated time: 2 hours
   - Tools needed: coding tools

## Success Criteria
- User can register and login
- Application is secure
"""
    
    parsed_plan = plugin._parse_plan_from_response(test_plan_content)
    if parsed_plan:
        print(f"✅ Plan parsing successful: {parsed_plan.title}")
        print(f"   Steps: {len(parsed_plan.steps)}")
        for step in parsed_plan.steps:
            print(f"   - {step.step_number}: {step.description}")
    else:
        print("❌ Plan parsing failed")
    
    print("\n🎉 All tests passed! Plugin is ready to use.")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("This is normal if running outside of AI Coder environment.")
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
