# boot.py
import asyncio
print("Booting up...")

try:
    import main
    print("main.py executed")
    
    # Manually start the event loop for the async `main()` function
    loop = asyncio.get_event_loop()
    loop.create_task(main.main())  # Start the async main task
    loop.run_forever()  # Keep the event loop running

except Exception as e:
    print("Error loading main.py:", e)