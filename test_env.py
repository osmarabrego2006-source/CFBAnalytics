import os
from dotenv import load_dotenv
import cfbd

def verify_environment_and_api():
    print("---Starting Environment Diagnostics---")
    load_dotenv()

    # extracting API key
    raw_key = os.getenv("CFBD_API_KEY")
    if not raw_key:
        print("Error: 'CFBD_API_KEY' not found in .env")
        return
    else:
        print("API Key successfully pulled from .env file")

    # CFBD API Authorization
    configuration = cfbd.Configuration(
        access_token = raw_key
    )

    api_client = cfbd.ApiClient(configuration)
    recruiting_api = cfbd.RecruitingApi(api_client)

    # executing sample live test call
    try:
        print("\nTesting live API Connection and sending request")
        response = recruiting_api.get_team_recruiting_rankings(year=2024)
        print("Success!")
        print("Received {} team records from 2024".format(len(response)))
        print("Sample Team Data: {} - {} points".format(response[0].team, response[0].points))
    except Exception as e:
        print("API Connection failed")
        print("Error: {}".format(e))

if __name__ == "__main__":
    verify_environment_and_api()