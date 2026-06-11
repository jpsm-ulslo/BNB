import logging
from src.nextbitt.client import NextbittClient

logging.basicConfig(level=logging.INFO)

def main():
    client = NextbittClient()
    data = client.run()
    print(f"Total rows: {len(data)}")

if __name__ == "__main__":
    main()