from services.robot_service import RobotService

robot = RobotService("10.1.4.122")  # ou IP da VM se estiver fora
if robot.connect():
    pose = robot.get_predefined_pose("center")
    if pose:
        robot.move_to_pose(pose)
    robot.disconnect()