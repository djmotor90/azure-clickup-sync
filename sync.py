import requests
import base64

# API Keys and Identifiers (replace with your actual values)
CLICKUP_API_KEY = 'your_clickup_api_key'
CLICKUP_LIST_ID = 'your_clickup_list_id'
CLICKUP_ENDPOINT = 'https://api.clickup.com/api/v2/'

AZURE_ORGANIZATION = 'your_azure_organization'
AZURE_PROJECT = 'your_azure_project'
AZURE_PERSONAL_ACCESS_TOKEN = 'your_azure_personal_access_token'
AZURE_PERSONAL_ACCESS_TOKEN_ENCODED = base64.b64encode(f':{AZURE_PERSONAL_ACCESS_TOKEN}'.encode()).decode()
AZURE_ENDPOINT = f'https://dev.azure.com/{AZURE_ORGANIZATION}/{AZURE_PROJECT}/_apis/wit/workitems/$Task?api-version=6.0'

# Headers for API Requests
azure_headers = {
    'Authorization': f'Basic {AZURE_PERSONAL_ACCESS_TOKEN_ENCODED}',
    'Content-Type': 'application/json-patch+json'
}

clickup_headers = {
    'Authorization': CLICKUP_API_KEY,
    'Content-Type': 'application/json'
}

def create_azure_task(task_title, task_description):
    """Create a task in Azure DevOps"""
    data = [
        {"op": "add", "path": "/fields/System.Title", "value": task_title},
        {"op": "add", "path": "/fields/System.Description", "value": task_description}
    ]
    response = requests.post(AZURE_ENDPOINT, json=data, headers=azure_headers)
    if response.ok:
        return response.json()
    print(f"Request failed: {response.status_code} - {response.content}")
    return None

def update_clickup_task_status(task_id):
    """Update the status of a task in ClickUp"""
    url = f'{CLICKUP_ENDPOINT}task/{task_id}'
    payload = {'status': 'COMPLETED'}
    response = requests.put(url, json=payload, headers=clickup_headers)
    if not response.ok:
        print(f'Failed to update ClickUp task: {response.status_code} - {response.content}')
        return None
    return response.json()

def get_azure_task_status(task_id):
    """Get the status of a task in Azure DevOps"""
    url = f'https://dev.azure.com/{AZURE_ORGANIZATION}/{AZURE_PROJECT}/_apis/wit/workitems/{task_id}?api-version=6.0'
    response = requests.get(url, headers=azure_headers)
    if not response.ok:
        print(f'Failed to get Azure task status: {response.status_code} - {response.content}')
        return None
    return response.json().get('fields', {}).get('System.State', 'Unknown')

def synchronize_azure_tasks():
    """Synchronize tasks between Azure DevOps and ClickUp"""
    query = {
        "query": "Select [System.Id], [System.Title], [System.State] From WorkItems Where [System.TeamProject] = @project"
    }
    query_endpoint = f'https://dev.azure.com/{AZURE_ORGANIZATION}/{AZURE_PROJECT}/_apis/wit/wiql?api-version=6.0'
    response = requests.post(query_endpoint, json=query, headers=azure_headers)
    if response.ok:
        work_items = response.json().get('workItems', [])
        for item in work_items:
            azure_task_id = item['id']
            status = get_azure_task_status(azure_task_id)
            if status == 'Doing':
                update_clickup_task_status(azure_task_id)
                print('ClickUp Task updated to completed.')
            print(f'Azure Task Status: {status}')
    else:
        print(f'Failed to get data from Azure. Status code: {response.status_code}')

def get_custom_field_ids(task_id):
    """Retrieve custom field IDs from a ClickUp task"""
    url = f'{CLICKUP_ENDPOINT}task/{task_id}'
    response = requests.get(url, headers=clickup_headers)
    if response.ok:
        task_data = response.json()
        custom_fields = task_data.get('custom_fields', [])
        for field in custom_fields:
            field_id = field.get('id')
            field_name = field.get('name')
            print(f"ID: {field_id}, Name: {field_name}")
        return custom_fields
    else:
        print(f'Failed to retrieve task details: {response.status_code} - {response.content}')
        return None

def update_clickup_custom_field(task_id, custom_field_id, value):
    """Update a custom field in a ClickUp task"""
    url = f'{CLICKUP_ENDPOINT}task/{task_id}/field/{custom_field_id}'
    payload = {'value': str(value)}
    response = requests.post(url, json=payload, headers=clickup_headers)
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Content: {response.content.decode('utf-8')}")
    if not response.ok:
        print(f'Failed to update ClickUp custom field: {response.status_code} - {response.content}')
        return None
    return response.json()

def synchronize_tasks():
    """Main function to synchronize tasks and update custom fields"""
    response = requests.get(f'{CLICKUP_ENDPOINT}list/{CLICKUP_LIST_ID}/task', headers=clickup_headers)
    if not response.ok:
        print(f'Failed to fetch ClickUp tasks: {response.status_code} - {response.content}')
        return None

    clickup_tasks = response.json().get('tasks', [])
    for task in clickup_tasks:
        task_id = task['id']
        task_title = task['name']
        task_description = task.get('description', '')
        custom_fields = get_custom_field_ids(task_id)
        target_custom_field_id = None
        for field in custom_fields:
            if field.get('name') == 'AZ_ID':  # Replace 'AZ_ID' with your actual custom field name
                target_custom_field_id = field.get('id')
                break

        if not target_custom_field_id:
            print(f"Custom field 'AZ_ID' not found for task {task_id}. Skipping...")
            continue

        azure_task = create_azure_task(task_title, task_description)
        if azure_task:
            azure_task_id = azure_task['id']
            print(f"Azure task created with ID: {azure_task_id}")
            update_clickup_custom_field(task_id, target_custom_field_id, azure_task_id)
            print(f"Updated ClickUp task {task_id} with Azure ID {azure_task_id}")

if __name__ == '__main__':
    synchronize_tasks()
