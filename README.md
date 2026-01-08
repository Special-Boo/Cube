# Cube
GridCube-Transparent

오른쪽 Release 탭 참고 (exe 실행)  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
concerning security issue,  
recommend virus scan, before using 'EXE' file (i recommend [use exe file with safe PC environment]) - see description below
or execute code with python-dev-venv yourself.  
  
  
---------------------- conversation with gpt --------------------------------  

  
1) 가장 큰 이슈: WinAPI로 “클릭스루/오버레이” 조작  
  
ctypes.windll.user32.GetWindowLongW / SetWindowLongW  
WS_EX_LAYERED | WS_EX_TRANSPARENT  
이 조합은 화면 위에 투명 오버레이를 얹고 입력을 통과시키는 전형적인 방식이라,  
일부 백신/EDR/게임 안티치트가 “의심 행동”으로 분류할 수 있음  
사용자 입장에서도 “화면 위에 떠있는 투명 창”은 피싱/치팅/스파이웨어 오해 받기 쉬움  
➡️ **배포 시 신뢰 이슈(오탐/차단/경고)**가 실제로 발생할 가능성이 있어.  
  
  
  
2) OpenGL + 오버레이는 게임/보안툴에서 특히 민감  
  
OpenGL 자체가 보안 문제는 아니지만, “항상 위 + 투명 + 트레이 상주”는  
화면 캡처/입력 훔치기 류로 오해되기 쉬움  
특히 게임 위에 뜨면 안티치트가 예민하게 봄  
  
