from fastapi import FastAPI
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI()

@app.get("/users/blood-group/{blood_group}")
def get_users(blood_group: str):

    response = requests.get(
        "https://dummyjson.com/users",
        verify=False
    )

    users = response.json()["users"]

    result = [
        {
            "id": user["id"],
            "name": f"{user['firstName']} {user['lastName']}",
            "bloodGroup": user["bloodGroup"]
        }
        for user in users
        if user["bloodGroup"] == blood_group
    ]

    print(f"\nFound {len(result)} users")

    for user in result:
        print(
            f"ID: {user['id']}, "
            f"Name: {user['name']}, "
            f"Blood Group: {user['bloodGroup']}"
        )

    return {
        "count": len(result),
        "users": result
    }


if __name__ == "__main__":
    result = get_users("AB-")

    # print(f"\nTotal Users: {result['count']}")

    # for user in result["users"]:
    #     print(
    #         f"ID: {user['id']}, "
    #         f"Name: {user['name']}, "
    #         f"Blood Group: {user['bloodGroup']}"
    #     )