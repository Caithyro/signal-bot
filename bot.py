import subprocess
import json
import time

# Use your phone number
account = ""  # Change to your signal phone number

signalPath = "bin/signal-cli" # Specify the folder with signal-cli

# Groups to recevie messages
groups = []

# Trusted senders list
trusted_senders = [
    "+380111111111",
    "+380222222222",
]

# Keywords for filtering messages
keywords = ["keyword1", "keyword2"]

# Startup message receiver
startup_receiver = ""

# Check if the sender is trusted
def is_trusted_sender(sender):
    return sender in trusted_senders

# Check if message has keywords
def contains_keyword(message):
    return any(keyword in message for keyword in keywords)

# Sending message on startup
def send_startup_message():
    try:
        command = [signalPath, "-a", account, "send", "-m", "Startup message", startup_receiver]
        subprocess.run(command, check=True)
        print("Message was sent successfully!")
    except subprocess.CalledProcessError as e:
        print(f"There is an error while sending message: {e}")

# Populating list of groups
def populate_groups():
    global groups
    groups.clear()
    try:
        result = subprocess.run(
            [signalPath, "-o", "json", "-a", account, "listGroups"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            print(f"Error while listing groups: {result.stderr.strip()}")
            return

        group_data = json.loads(result.stdout)

        # Add groups to list if isMember = true
        groups = [group['id'] for group in group_data if group.get('isMember')]

        print(f"Groups populated: {groups}")

    except Exception as e:
        print(f"An error occurred while populating groups: {e}")

# Resend received message to groups from the list
def send_message_to_groups(message):
    global groups
    for group in groups:
        try:
            result = subprocess.run(
                [signalPath, "-a", account, "send", "-m", message, "-g", group],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode == 0:
                print(f"Message sent succesfully to group {group}.")
            else:
                print(f"Error sending message to group {group}.")
                print("Error:", result.stderr)
        except Exception as e:
            print(f"An error occurred: {e}") 
    print("Broadcast ended")

# Synchronization
def send_sync_request():
    try:
        subprocess.run(
            [signalPath, "-a", account, "sendSyncRequest"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print("Sync request sent.")
        time.sleep(1)
        print("Sync request wait ended.")
    except Exception as e:
        print(f"An error occurred while sending sync request: {e}")

# Receiving messages and sending them
def receive_messages():
    try:
        result = subprocess.run(
            [signalPath, "-o", "json", "-a", account, "receive", "--ignore-attachments", "--ignore-stories", "--send-read-receipts"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            print(f"Error: {result.stderr.strip()}")
            return

        messages = result.stdout.strip().splitlines()
        for message in messages:
            try:
                data = json.loads(message)
                sender = data['envelope']['source']

                if is_trusted_sender(sender):
                    if 'dataMessage' in data['envelope'] and 'message' in data['envelope']['dataMessage']:
                        text_message = data['envelope']['dataMessage']['message']
                        if contains_keyword(text_message):
                            print(f"Received message from trusted sender {sender}")
                            send_message_to_groups(text_message)
                        else:
                            print(f"Message does not contain keywords")
                    else:
                        print(f"Received a non-text message from {sender}")
                else:
                    print(f"Message from untrusted sender {sender}")

            except json.JSONDecodeError:
                print("Received non-JSON message:", message)
            except KeyError:
                print("Message format error:", message)

    except Exception as e:
        print(f"An error occurred: {e}")

# Startup cycle
send_startup_message()  # Message on startup
send_sync_request() # Synchronization
populate_groups()  # Populating groups

# Main cycle
last_populate_time = time.time()
while True:
    receive_messages()

    if time.time() - last_populate_time >= 43200:  # 43200 seconds = 12 hours
        send_sync_request()
        populate_groups()
        last_populate_time = time.time()

    time.sleep(30)  # Waiting 30 seconds before the next call
