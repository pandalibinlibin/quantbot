#!/usr/bin/env python3
"""
Inspect SoftTopkStrategy to understand its parameters and behavior
"""

import inspect
from qlib.contrib.strategy import SoftTopkStrategy

def inspect_softtopk():
    """Inspect SoftTopkStrategy class"""
    
    print("🔍 SoftTopkStrategy Class Inspection")
    print("=" * 50)
    
    # Get constructor signature
    print("\n📋 Constructor Signature:")
    sig = inspect.signature(SoftTopkStrategy.__init__)
    print(f"SoftTopkStrategy.__init__{sig}")
    
    # Get constructor source code
    print("\n📄 Constructor Source Code:")
    try:
        source = inspect.getsource(SoftTopkStrategy.__init__)
        print(source)
    except Exception as e:
        print(f"❌ Cannot get source: {e}")
    
    # Get class docstring
    print("\n📚 Class Documentation:")
    print(SoftTopkStrategy.__doc__ or "No documentation available")
    
    # Get all methods
    print("\n🔧 Available Methods:")
    methods = [method for method in dir(SoftTopkStrategy) if not method.startswith('_')]
    for method in methods:
        print(f"  - {method}")
    
    # Check parent classes
    print("\n🏗️ Class Hierarchy:")
    print(f"MRO: {[cls.__name__ for cls in SoftTopkStrategy.__mro__]}")

if __name__ == "__main__":
    inspect_softtopk()
