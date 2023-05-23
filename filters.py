from datetime import datetime

def format_timestamp(value):
    # Convert the timestamp to a datetime object
    timestamp = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    
    # Format the datetime object
    if timestamp.year != datetime.now().year:
        formatted_timestamp = timestamp.strftime("%B %dth, %Y")
    else:
        formatted_timestamp = timestamp.strftime("%B %dth")

    return formatted_timestamp
