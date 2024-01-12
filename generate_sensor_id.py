import uuid

def generate_sensor_id():
    return str(uuid.uuid4())

if __name__ == '__main__':
    print(generate_sensor_id())
