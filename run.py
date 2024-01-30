import subprocess

def main():
    # List of scripts to run
    scripts = ['script1.py', 'script2.py', 'script3.py']

    # Run each script as a separate process
    processes = [run_script(script) for script in scripts]

    # Optionally, wait for them to complete
    for process in processes:
        process.wait()

if __name__ == '__main__':
    main()

