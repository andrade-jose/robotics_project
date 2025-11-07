# Vision System V2 - Complete Architecture

**Status**: ✅ COMPLETE AND TESTED (Phase 3 + Phase 4)

---

## System Overview

The V2 Vision System is a modular, testable architecture for ArUco-based board game vision. It consists of two major subsystems:

### **Subsystem 1: Vision Capture & Detection (Phase 3)**
- Camera capture (simple, hardware-independent)
- ArUco marker detection
- Grid coordinate mapping
- Vision manager orchestration

### **Subsystem 2: Calibration & Workspace (Phase 4)**
- 2-marker calibration (automatic transformation)
- Board transformation matrix (camera pixels → physical mm)
- 3×3 grid generation
- Workspace validation (movement safety)

---

## Architecture Diagram

```
Camera Frame
    ↓
    ├─→ [VisionManager] ──────┐
    │   - Thread-safe state    │
    │   - Camera init/release   │
    │                           ↓
    ├─→ [CameraSimple] ──────→ [Frame Buffer]
    │   - OpenCV capture        │
    │   - FPS control           ↓
    │                      ┌────┴─────┐
    ├─→ [ArUcoDetector] ──→│ Detection │
    │   - Marker detect         │ Results │
    │   - Centroid calc         └────┬─────┘
    │   - Validation            ↓
    └─→ [GridCalculator] ──→ [Grid State]
        - Centroid→Cell       {pos: value}
        - State validation
                              ↓
                        [Game Logic]
                              ↓
                        (Need Calibration)
                              ↓
    Camera Frame
         ↓
    [CalibrationMarkerDetector]
    - Detect exactly 2 markers
    - Extract poses
    - Smoothing (3-5 frames)
         ↓
    [CalibrationData] {marker0, marker1, scale, confidence}
         ↓
    [BoardTransformCalculator]
    - Build transformation matrix
    - Pixel ↔ Board conversion
    - Validation (roundtrip)
         ↓
    [TransformMatrix] {origin, scale, axis_x, axis_y, axis_z}
         ↓
    [GridGenerator]
    - Generate 9 cell positions (mm)
    - Position ↔ Pixel mapping
    - Grid validation
         ↓
    [GridCell] × 9 {position, center_mm, is_valid}
         ↓
    [WorkspaceValidator]
    - Define physical limits
    - Validate positions
    - Validate movements
    - Collision detection
         ↓
    [CalibrationOrchestrator]
    - Complete pipeline
    - State management
    - High-level API for game
         ↓
    [Game] ← is_move_valid(), get_valid_moves()
```

---

## Complete Component List

### Phase 3: Vision (4 modules)

#### 1. CameraSimple (260 LOC)
- **Purpose**: Hardware-independent camera capture
- **Methods**: initialize_camera(), capture_frame(), scan_available_cameras(), release()
- **Status**: ✅ Complete, 35 tests passing

#### 2. ArUcoDetector (280 LOC)
- **Purpose**: Detect individual ArUco markers and extract centroids
- **Methods**: detect(), validate_detections(), draw_detections(), get_stats()
- **Status**: ✅ Complete, 32 tests passing

#### 3. GridCalculator (310 LOC)
- **Purpose**: Map centroid pixels to 3×3 grid positions (0-8)
- **Methods**: centroid_to_cell(), cell_to_centroid(), calculate_state(), validate_state()
- **Features**: Bidirectional mapping, state validation, position queries
- **Status**: ✅ Complete, 38 tests passing

#### 4. VisionManager (290 LOC)
- **Purpose**: Orchestrate vision modules with thread safety
- **Methods**: start(), stop(), process_frame_sync(), get_current_state(), get_stats()
- **Features**: Threading support, RLock for state safety, context manager
- **Status**: ✅ Complete

---

### Phase 4: Calibration (5 modules)

#### 1. CalibrationMarkerDetector (400+ LOC)
- **Purpose**: Detect exactly 2 ArUco markers for board calibration
- **Methods**: detect(), validate_calibration(), get_axis_vectors(), draw_calibration()
- **Features**:
  - Exactly 2 markers required (fails gracefully otherwise)
  - Moving average smoothing (3-5 frames)
  - Distance validation (50-2000 pixels)
  - Fallback to last valid calibration
- **Status**: ✅ Complete, 10 tests passing

#### 2. BoardTransformCalculator (300+ LOC)
- **Purpose**: Build and manage camera→board transformation matrix
- **Methods**: pixel_to_board(), board_to_pixel(), validate_transform(), get_transform_info()
- **Features**:
  - Linear transformation based on 2 markers
  - Roundtrip validation (error < 1 pixel)
  - Detailed transform information
  - Scale and axis extraction
- **Status**: ✅ Complete, 5 tests passing

#### 3. GridGenerator (380+ LOC)
- **Purpose**: Generate 3×3 grid positions in physical coordinates (mm)
- **Methods**: get_grid_positions(), get_cell_position(), pixel_to_position(), validate_grid()
- **Features**:
  - 9 cell centers calculated from 2 markers
  - Bidirectional position↔pixel mapping
  - Cell size = distance_mm / 3
  - Bounds checking
- **Status**: ✅ Complete, 7 tests passing

#### 4. WorkspaceValidator (350+ LOC)
- **Purpose**: Validate positions and movements within physical workspace
- **Methods**: is_position_valid(), can_move(), get_valid_moves(), update_piece_positions()
- **Features**:
  - Physical limit checking
  - Safety margins (10mm default)
  - Collision detection
  - Dynamic piece position tracking
  - Movement validation
- **Status**: ✅ Complete, 9 tests passing

#### 5. CalibrationOrchestrator (280+ LOC)
- **Purpose**: Orchestrate complete calibration pipeline
- **Methods**: calibrate(), is_move_valid(), get_valid_moves(), get_calibration_status()
- **Features**:
  - Complete 4-stage pipeline
  - State management (NOT_CALIBRATED → CALIBRATED)
  - Fallback to last valid calibration
  - High-level API for game
  - Detailed logging with [TAG] prefixes
- **Status**: ✅ Complete, 4 tests passing

---

## Complete Test Coverage

### Phase 3 Tests: 105 tests (100% passing)
```
test_camera.py         35 tests ✅
test_aruco.py          32 tests ✅
test_grid.py           38 tests ✅
```

### Phase 4 Tests: 35 tests (100% passing)
```
TestCalibrationMarkerDetector      10 tests ✅
TestBoardTransformCalculator        5 tests ✅
TestGridGenerator                   7 tests ✅
TestWorkspaceValidator              9 tests ✅
TestCalibrationOrchestrator         4 tests ✅
```

### Total: 140 tests (100% passing) ✅

---

## Data Flow Example

### Scenario: Game Move Validation

```python
# Input: User wants to move from position 0 to position 4
orchestrator = CalibrationOrchestrator(distance_mm=270.0)

# 1. Must be calibrated first
frame = camera.capture_frame()
calib_result = orchestrator.calibrate(frame)
# → CalibrationData extracted
# → TransformMatrix built
# → Grid generated (9 positions)
# → Workspace validated

# 2. During game play
occupied_positions = {0, 8}  # Pieces on board
from_position = 0
to_position = 4

# 3. Validate move
is_valid = orchestrator.is_move_valid(
    from_position,
    to_position,
    occupied_positions
)
# → WorkspaceValidator.can_move() checks:
#    - Both positions are valid (0-8)
#    - Destination not occupied
#    - Movement allowed
# → Returns: True or False

if is_valid:
    # Get actual board coordinates for robot
    coords = orchestrator.get_grid_position(4)
    # → Returns: (x_mm, y_mm, 0.0)
    # → Send to RobotService
```

---

## Configuration Parameters

### CalibrationMarkerDetector
```python
CalibrationMarkerDetector(
    aruco_dict_size=6,          # 6×6 bits
    marker_size=250,            # Marker code
    distance_mm=270.0,          # Real distance between markers
    smoothing_frames=3,         # 3-5 frame averaging
)
```

### WorkspaceValidator
```python
WorkspaceValidator(
    grid_generator,
    safety_margin_mm=10.0,      # 10mm safety zone
)
```

### CalibrationOrchestrator
```python
CalibrationOrchestrator(
    distance_mm=270.0,
    smoothing_frames=3,
    safety_margin_mm=10.0,
)
```

---

## Physics Implemented

### Coordinate System
```
Board Coordinates (mm):
    (0,270) ─────────────── (270,270)
      │                       │
      │      3×3 Grid        │
      │                       │
    (0,0) ──────────────── (270,0)

Grid Layout (positions 0-8):
    0 | 1 | 2
    ---------
    3 | 4 | 5
    ---------
    6 | 7 | 8

Cell Size: 270mm / 3 = 90mm
Cell Center (position i):
    col = i % 3
    row = i // 3
    x = (col + 0.5) * 90mm
    y = (row + 0.5) * 90mm
```

### Transformation
```
Pixel → Board (mm):
    1. Vector from marker0 to pixel (relative)
    2. Project on X axis: dot(rel, axis_x) * scale
    3. Project on Y axis: dot(rel, axis_y) * scale
    4. Result: (board_x, board_y, 0.0)

Board → Pixel:
    1. Divide by scale: x_norm = board_x / scale
    2. Reconstruct vector: vec = x_norm*axis_x + y_norm*axis_y
    3. Add to origin: pixel = origin + vec
```

---

## Error Handling

### Graceful Degradation
| Failure | Behavior |
|---------|----------|
| No 2 markers found | Use last valid calibration |
| Transform invalid | Fail pipeline, log error |
| Grid out of bounds | Fail validation |
| Movement collision | Reject move, return valid alternatives |
| Thread error | Error logged, fallback state used |

---

## Logging Tags

```
[CALIB]      CalibrationMarkerDetector (detection, smoothing)
[TRANSFORM]  BoardTransformCalculator (matrix, validation)
[GRID]       GridGenerator (position generation, validation)
[WORKSPACE]  WorkspaceValidator (movement, collision)
[VISION]     VisionManager (orchestration, threading)
[CAMERA]     CameraSimple (hardware control)
[ARUCO]      ArUcoDetector (detection, validation)
```

---

## Integration Points

### With GameOrchestrator
```python
# In GameOrchestrator.process_move()
if calibrator.is_move_valid(from_pos, to_pos, occupied):
    board_coords = calibrator.get_grid_position(to_pos)
    # Send to RobotService
```

### With RobotService
```python
# In RobotService.move_piece()
board_coords = calibrator.get_grid_position(position)
# Convert board_coords (mm) to robot coordinates
# Execute movement
```

### With VisionManager
```python
# Use VisionManager for continuous frame capture
vision_manager = VisionManager(use_threading=False)
vision_manager.start()

# Calibrate once at game start
frame = vision_manager.camera.capture_frame()
calib_result = calibrator.calibrate(frame)

# Then use calibrator for move validation
```

---

## Performance Metrics

| Operation | Time |
|-----------|------|
| Detect 2 markers | ~30-50ms |
| Build transformation | ~5ms |
| Generate grid | ~2ms |
| Validate movement | ~1ms |
| Complete calibration | ~100ms |
| Test suite | 1.72s |

---

## Future Extensions

### Planned (Phase 5+)
- [ ] Multi-marker robust calibration (3+ markers)
- [ ] Dynamic recalibration during game
- [ ] Perspective correction for tilted board
- [ ] Temperature/lighting compensation
- [ ] Real-time calibration quality monitoring

### Optional Enhancements
- [ ] Machine learning-based marker detection
- [ ] Sub-pixel accuracy for better calibration
- [ ] Confidence-based movement restrictions
- [ ] Adaptive smoothing (frame-adaptive, not fixed)
- [ ] GPU acceleration for image processing

---

## File Structure

```
v2/vision/
├── __init__.py
│
├── camera_simple.py                     ← Phase 3
├── aruco_detector.py                    ← Phase 3
├── grid_calculator.py                   ← Phase 3
├── vision_manager.py                    ← Phase 3
│
├── calibration_marker_detector.py       ← Phase 4
├── board_transform_calculator.py        ← Phase 4
├── grid_generator.py                    ← Phase 4
├── workspace_validator.py               ← Phase 4
├── calibration_orchestrator.py          ← Phase 4
│
├── tests/
│   ├── __init__.py
│   ├── test_camera.py                   ← Phase 3 (35 tests)
│   ├── test_aruco.py                    ← Phase 3 (32 tests)
│   ├── test_grid.py                     ← Phase 3 (38 tests)
│   └── test_calibration.py              ← Phase 4 (35 tests)
│
├── CALIBRATION_SYSTEM.md                ← Phase 4 docs
└── README_COMPLETE_SYSTEM.md            ← This file
```

---

## Summary

✅ **140 tests** passing (100%)
✅ **~3,500+ lines** of production code
✅ **5 core modules** (Phase 4 calibration)
✅ **Complete documentation**
✅ **Physics-based transformation**
✅ **Safety validation**
✅ **Thread-safe operations**
✅ **Graceful error handling**

**Status**: READY FOR GAME INTEGRATION

---

**Version**: v2.0
**Phase**: 4 Complete
**Date**: 2025-11-07
**Commit**: 101b874
