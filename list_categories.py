import subprocess
import sys

def main():
    if len(sys.argv) < 3:
        print("Usage: nixpkger list-categories <category-file>")
        sys.exit(1)

    action = sys.argv[1]
    category_file = sys.argv[2]

    if action == "list-categories":
        subprocess.run(["bash", "/scripts/resources/category-finder", category_file])
    else:
        print("Unknown action")

if __name__ == "__main__":
    main()
