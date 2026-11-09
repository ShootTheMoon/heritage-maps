# 화성 v25 Studio 벌크 임포트 순서 (세션당 ≤12 파일, 세션 사이 저장→Studio 재시작, 재임포트 금지)

배치 0 = 프로브 3개(지형 타일 1 · 담장 마스터 1 · 여장 1). 배치 후 `-Resolve` 성 확인은 `python hws_place.py <UGCLocalAssetTable.json>` 의 UNRESOLVED 수로 본다.
식생 848개는 산곡 MST_* 에셋 재사용 — 임포트 금지.

## 배치 0 (3 파일)
- [ ] `03_TERRAIN\HWS_TER_11.fbx`  tris 3200
- [ ] `10_MASTERS\HWS_NH_PARAPET.fbx`  tris 1766
- [ ] `10_MASTERS\HWS_NH_WALL.fbx`  tris 14767

## 배치 1 (12 파일)
- [ ] `10_MASTERS\HWS_BK_HayBale.fbx`  tris 736
- [ ] `10_MASTERS\HWS_BK_MudPots11.fbx`  tris 2880
- [ ] `10_MASTERS\HWS_BK_OldWoodenBarrel.fbx`  tris 6904
- [ ] `10_MASTERS\HWS_NH_SECRETGATE.fbx`  tris 13753
- [ ] `02_DOORS\HWS_DOOR_MG_L_P54.fbx`  tris 238
- [ ] `02_DOORS\HWS_DOOR_MG_L_P55.fbx`  tris 716
- [ ] `02_DOORS\HWS_DOOR_MG_R_P54.fbx`  tris 120
- [ ] `02_DOORS\HWS_DOOR_MG_R_P55.fbx`  tris 652
- [ ] `02_DOORS\HWS_DOOR_OS_L_P54.fbx`  tris 120
- [ ] `02_DOORS\HWS_DOOR_OS_L_P55.fbx`  tris 604
- [ ] `02_DOORS\HWS_DOOR_OS_R_P54.fbx`  tris 238
- [ ] `02_DOORS\HWS_DOOR_OS_R_P55.fbx`  tris 744

## 배치 2 (12 파일)
- [ ] `03_TERRAIN\HWS_OUT_00.fbx`  tris 1250
- [ ] `03_TERRAIN\HWS_OUT_01.fbx`  tris 1250
- [ ] `03_TERRAIN\HWS_OUT_02.fbx`  tris 1250
- [ ] `03_TERRAIN\HWS_OUT_10.fbx`  tris 950
- [ ] `03_TERRAIN\HWS_OUT_12.fbx`  tris 950
- [ ] `03_TERRAIN\HWS_OUT_20.fbx`  tris 950
- [ ] `03_TERRAIN\HWS_OUT_22.fbx`  tris 950
- [ ] `03_TERRAIN\HWS_OUT_30.fbx`  tris 1250
- [ ] `03_TERRAIN\HWS_OUT_31.fbx`  tris 1250
- [ ] `03_TERRAIN\HWS_OUT_32.fbx`  tris 1250
- [ ] `03_TERRAIN\HWS_TER_00.fbx`  tris 3200
- [ ] `03_TERRAIN\HWS_TER_01.fbx`  tris 3200

## 배치 3 (12 파일)
- [ ] `03_TERRAIN\HWS_TER_02.fbx`  tris 3200
- [ ] `03_TERRAIN\HWS_TER_03.fbx`  tris 2400
- [ ] `03_TERRAIN\HWS_TER_10.fbx`  tris 3200
- [ ] `03_TERRAIN\HWS_TER_12.fbx`  tris 3200
- [ ] `03_TERRAIN\HWS_TER_13.fbx`  tris 2400
- [ ] `03_TERRAIN\HWS_TER_20.fbx`  tris 3200
- [ ] `03_TERRAIN\HWS_TER_21.fbx`  tris 3200
- [ ] `03_TERRAIN\HWS_TER_22.fbx`  tris 3200
- [ ] `03_TERRAIN\HWS_TER_23.fbx`  tris 2400
- [ ] `03_TERRAIN\HWS_TER_30.fbx`  tris 3200
- [ ] `03_TERRAIN\HWS_TER_31.fbx`  tris 3200
- [ ] `03_TERRAIN\HWS_TER_32.fbx`  tris 3200

## 배치 4 (12 파일)
- [ ] `03_TERRAIN\HWS_TER_33.fbx`  tris 2400
- [ ] `03_TERRAIN\HWS_TER_40.fbx`  tris 3200
- [ ] `03_TERRAIN\HWS_TER_41.fbx`  tris 3200
- [ ] `03_TERRAIN\HWS_TER_42.fbx`  tris 3200
- [ ] `03_TERRAIN\HWS_TER_43.fbx`  tris 2400
- [ ] `01_JAM\HWS_JAM_00_MI_T_Roof.fbx`  tris 25920
- [ ] `01_JAM\HWS_JAM_01_MI_T_Roof.fbx`  tris 25920
- [ ] `01_JAM\HWS_JAM_02_MI_T_Roof.fbx`  tris 25920
- [ ] `01_JAM\HWS_JAM_03_MI_T_Roof.fbx`  tris 25920
- [ ] `01_JAM\HWS_JAM_04_MI_T_CW_002_001.fbx`  tris 14113
- [ ] `01_JAM\HWS_JAM_05_MI_T_CW_003_001.fbx`  tris 18306
- [ ] `01_JAM\HWS_JAM_06_MI_T_Ridge.fbx`  tris 15054

## 배치 5 (12 파일)
- [ ] `01_JAM\HWS_JAM_07_MI_T_Cannon.fbx`  tris 25920
- [ ] `01_JAM\HWS_JAM_08_MI_T_CW_001_001.fbx`  tris 2940
- [ ] `01_JAM\HWS_JAM_09_MI_T_GH_Wall.fbx`  tris 25920
- [ ] `01_JAM\HWS_JAM_10_MI_T_ComplexBracket.fbx`  tris 25920
- [ ] `01_JAM\HWS_JAM_11_MI_T_ComplexBracket.fbx`  tris 25920
- [ ] `01_JAM\HWS_JAM_12_MI_T_ComplexBracket.fbx`  tris 25919
- [ ] `01_JAM\HWS_JAM_13_MI_T_ComplexBracket.fbx`  tris 25920
- [ ] `01_JAM\HWS_JAM_14_MI_T_ComplexBracket.fbx`  tris 25920
- [ ] `01_JAM\HWS_JAM_15_MI_T_ComplexBracket.fbx`  tris 25920
- [ ] `01_JAM\HWS_JAM_16_MI_T_ComplexBracket.fbx`  tris 25920
- [ ] `01_JAM\HWS_JAM_17_MI_T_ComplexBracket.fbx`  tris 25920
- [ ] `01_JAM\HWS_JAM_18_MI_T_Floor.fbx`  tris 3902

## 배치 6 (12 파일)
- [ ] `01_JAM\HWS_JAM_19_MI_T_Fortification_002_001.fbx`  tris 468
- [ ] `01_JAM\HWS_JAM_20_MI_T_Pedestal.fbx`  tris 3936
- [ ] `01_JAM\HWS_JAM_21_MI_T_GH_Parapet_001_001.fbx`  tris 15936
- [ ] `01_JAM\HWS_JAM_22_MI_T_B_Parapet_001_001.fbx`  tris 23595
- [ ] `01_JAM\HWS_JAM_23_MI_T_WoodStair.fbx`  tris 25919
- [ ] `01_JAM\HWS_JAM_24_MI_T_Column.fbx`  tris 21864
- [ ] `01_JAM\HWS_JAM_25_MI_T_Rafter.fbx`  tris 25920
- [ ] `01_JAM\HWS_JAM_26_MI_T_SideDoor.fbx`  tris 26248
- [ ] `01_JAM\HWS_JAM_27_MI_T_PurlinSupport.fbx`  tris 11748
- [ ] `01_JAM\HWS_JAM_28_MI_T_RoofStatue.fbx`  tris 25920
- [ ] `01_JAM\HWS_JAM_29_MI_T_Heartwood.fbx`  tris 580
- [ ] `01_JAM\HWS_JAM_30_MI_T_Roof.fbx`  tris 25920

## 배치 7 (12 파일)
- [ ] `01_JAM\HWS_JAM_31_MI_T_Crossbeam.fbx`  tris 15688
- [ ] `01_JAM\HWS_JAM_32_MI_T_Lintel.fbx`  tris 17022
- [ ] `01_JAM\HWS_JAM_33_MI_T_RoofBoard.fbx`  tris 25920
- [ ] `01_JAM\HWS_JAM_34_MI_Flag_01_001.fbx`  tris 25920
- [ ] `01_JAM\HWS_JAM_35_MI_Flag_01_001.fbx`  tris 13988
- [ ] `01_JAM\HWS_JAM_36_MI_T_B_Parapet_002_001.fbx`  tris 19872
- [ ] `01_JAM\HWS_JAM_37_MI_T_B_GateHouse_004_001.fbx`  tris 1024
- [ ] `01_JAM\HWS_JAM_38_MI_T_RammedEarth.fbx`  tris 584
- [ ] `01_JAM\HWS_JAM_39_MI_T_G_Stair_001_001.fbx`  tris 7108
- [ ] `01_JAM\HWS_JAM_40_MI_T_Purlin.fbx`  tris 16840
- [ ] `01_JAM\HWS_JAM_41_MI_T_Roof.fbx`  tris 25920
- [ ] `01_JAM\HWS_JAM_42_MI_T_Ceiling.fbx`  tris 1356

## 배치 8 (12 파일)
- [ ] `01_JAM\HWS_JAM_43_MI_T_B_CastleWall_002_001.fbx`  tris 25919
- [ ] `01_JAM\HWS_JAM_44_MI_T_GateGuardPost_001.fbx`  tris 1816
- [ ] `01_JAM\HWS_JAM_45_MI_T_Fortification_001_001.fbx`  tris 6826
- [ ] `01_JAM\HWS_JAM_46_MI_T_G_MetalDoor_001_001.fbx`  tris 0
- [ ] `01_JAM\HWS_JAM_47_MI_T_G_MetalDoor_002_001.fbx`  tris 0
- [ ] `01_JAM\HWS_JAM_48_MI_T_B_GateHouse_003_001.fbx`  tris 2549
- [ ] `01_JAM\HWS_JAM_49_MI_T_G_Stair_002_001.fbx`  tris 5296
- [ ] `01_JAM\HWS_JAM_50_MI_T_B_ArchDoor_001_001.fbx`  tris 5556
- [ ] `01_JAM\HWS_JAM_51_MI_T_CW_004_001.fbx`  tris 7556
- [ ] `01_JAM\HWS_JAM_52_MI_T_Roof.fbx`  tris 25920
- [ ] `01_JAM\HWS_JAM_53_MI_T_B_GateHouse_002_001.fbx`  tris 6644
- [ ] `01_JAM\HWS_JAM_54_MI_T_Note.fbx`  tris 108

## 배치 9 (12 파일)
- [ ] `01_JAM\HWS_JAM_55_MI_T_B_CastleWall_001_001.fbx`  tris 26321
- [ ] `01_JAM\HWS_JAM_56_MI_T_B_Floor_001.fbx`  tris 2303
- [ ] `01_JAM\HWS_JAM_57_MI_T_G_RoofBoard_001_001.fbx`  tris 12
- [ ] `01_JAM\HWS_JAM_58_MI_T_B_GateHouse_001_001.fbx`  tris 25920
- [ ] `01_JAM\HWS_JAM_59_MI_T_G_Arch_001_001.fbx`  tris 432
- [ ] `01_JAM\HWS_JAM_60_MI_T_B_RoofBoard_001_001.fbx`  tris 2562
- [ ] `01_JAM\HWS_JAM_61_MI_T_B_Arch_001.fbx`  tris 1122
- [ ] `01_JAM\HWS_JAM_62_MI_T_Signboard_002.fbx`  tris 1500
- [ ] `01_JAM\HWS_JAM_63_MI_T_Roof.fbx`  tris 25920
- [ ] `01_JAM\HWS_JAM_64_WorldGridMaterial.fbx`  tris 4
- [ ] `01_JAM\HWS_JAM_65_MI_T_Roof.fbx`  tris 25919
- [ ] `01_JAM\HWS_JAM_66_MI_T_Roof.fbx`  tris 25920
