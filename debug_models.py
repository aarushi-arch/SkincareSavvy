try:
    import sys
    # Add project root to sys.path
    import os
    sys.path.append(os.getcwd())
    
    print("Attempting to import users.models...")
    import users.models
    print("SUCCESS: users.models imported")
    
    if hasattr(users.models, 'Notification'):
        print("SUCCESS: Notification found in users.models")
    else:
        print("FAILURE: Notification NOT found in users.models")
        print(f"Available names: {dir(users.models)}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
