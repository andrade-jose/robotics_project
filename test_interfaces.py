"""
Test script to verify interface implementations.
"""

from interfaces.robot_interfaces import (
    IRobotController,
    IRobotValidator,
    IGameService,
    IDiagnostics
)

def test_interface_implementation():
    """Verify all classes implement their interfaces correctly."""

    print("=" * 60)
    print("Testing Interface Implementations")
    print("=" * 60)

    all_passed = True

    # Test URController implements IRobotController
    try:
        from logic_control.ur_controller import URController
        print("\n[OK] URController imports successfully")
        is_subclass = issubclass(URController, IRobotController)
        print(f"  - Implements IRobotController: {is_subclass}")
        if not is_subclass:
            all_passed = False

        # Check required methods exist
        required_methods = ['connect', 'disconnect', 'is_connected', 'move_to_pose',
                          'get_current_pose', 'get_current_joints', 'stop_movement',
                          'emergency_stop']
        for method in required_methods:
            has_method = hasattr(URController, method)
            status = "[OK]" if has_method else "[FAIL]"
            print(f"  {status} {method}")
            if not has_method:
                all_passed = False
    except Exception as e:
        print(f"\n[FAIL] URController: {e}")
        all_passed = False

    # Test PoseValidationService implements IRobotValidator
    try:
        from services.pose_validation_service import PoseValidationService
        print("\n[OK] PoseValidationService imports successfully")
        is_subclass = issubclass(PoseValidationService, IRobotValidator)
        print(f"  - Implements IRobotValidator: {is_subclass}")
        if not is_subclass:
            all_passed = False

        # Check required methods exist
        required_methods = ['validate_pose', 'validate_coordinates', 'validate_orientation',
                          'check_reachability', 'check_safety_limits']
        for method in required_methods:
            has_method = hasattr(PoseValidationService, method)
            status = "[OK]" if has_method else "[FAIL]"
            print(f"  {status} {method}")
            if not has_method:
                all_passed = False
    except Exception as e:
        print(f"\n[FAIL] PoseValidationService: {e}")
        all_passed = False

    # Test RobotService implements IGameService
    try:
        from services.robot_service import RobotService
        print("\n[OK] RobotService imports successfully")
        is_subclass = issubclass(RobotService, IGameService)
        print(f"  - Implements IGameService: {is_subclass}")
        if not is_subclass:
            all_passed = False

        # Check required methods exist
        required_methods = ['initialize', 'shutdown', 'get_status', 'move_to_board_position',
                          'place_piece', 'move_piece', 'return_to_home']
        for method in required_methods:
            has_method = hasattr(RobotService, method)
            status = "[OK]" if has_method else "[FAIL]"
            print(f"  {status} {method}")
            if not has_method:
                all_passed = False
    except Exception as e:
        print(f"\n[FAIL] RobotService: {e}")
        all_passed = False

    # Test RobotDiagnostics implements IDiagnostics
    try:
        from diagnostics.robot_diagnostics import RobotDiagnostics
        print("\n[OK] RobotDiagnostics imports successfully")
        is_subclass = issubclass(RobotDiagnostics, IDiagnostics)
        print(f"  - Implements IDiagnostics: {is_subclass}")
        if not is_subclass:
            all_passed = False

        # Check required methods exist
        required_methods = ['register_movement', 'register_validation',
                          'get_movement_statistics', 'generate_safety_report',
                          'reset_statistics', 'export_history']
        for method in required_methods:
            has_method = hasattr(RobotDiagnostics, method)
            status = "[OK]" if has_method else "[FAIL]"
            print(f"  {status} {method}")
            if not has_method:
                all_passed = False
    except Exception as e:
        print(f"\n[FAIL] RobotDiagnostics: {e}")
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED - Interface compliance verified")
    else:
        print("SOME TESTS FAILED - Check output above")
    print("=" * 60)

    return all_passed

if __name__ == "__main__":
    test_interface_implementation()
