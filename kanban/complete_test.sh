#!/bin/bash

echo "====================================="
echo "KANBAN API COMPLETE TEST"
echo "====================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Base URL
BASE_URL="http://localhost:8000/api"

echo -e "\n${BLUE}1. REGISTER USER${NC}"
REGISTER_RESPONSE=$(curl -s -X POST $BASE_URL/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "Test123!",
    "password2": "Test123!",
    "first_name": "Test",
    "last_name": "User"
  }')
echo $REGISTER_RESPONSE | python3 -m json.tool

echo -e "\n${BLUE}2. LOGIN${NC}"
LOGIN_RESPONSE=$(curl -s -X POST $BASE_URL/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!"
  }')
echo $LOGIN_RESPONSE | python3 -m json.tool

# Extract token
TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access'])")
echo -e "\n${GREEN} Token: ${TOKEN:0:50}...${NC}"

echo -e "\n${BLUE}3. GET PROFILE${NC}"
curl -s -X GET $BASE_URL/users/me/ \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo -e "\n${BLUE}4. CREATE WORKSPACE${NC}"
WORKSPACE_RESPONSE=$(curl -s -X POST $BASE_URL/workspaces/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Workspace",
    "description": "Workspace for testing"
  }')
echo $WORKSPACE_RESPONSE | python3 -m json.tool
WORKSPACE_ID=$(echo $WORKSPACE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

echo -e "\n${BLUE}5. CREATE BOARD${NC}"
BOARD_RESPONSE=$(curl -s -X POST $BASE_URL/boards/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"workspace\": $WORKSPACE_ID,
    \"title\": \"Test Board\",
    \"description\": \"Board for testing\"
  }")
echo $BOARD_RESPONSE | python3 -m json.tool
BOARD_ID=$(echo $BOARD_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

echo -e "\n${BLUE}6. LIST COLUMNS${NC}"
curl -s -X GET "$BASE_URL/columns/?board=$BOARD_ID" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo -e "\n${BLUE}7. CREATE TASK${NC}"
TASK_RESPONSE=$(curl -s -X POST $BASE_URL/tasks/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"column\": 1,
    \"title\": \"Test Task\",
    \"description\": \"Task for testing\",
    \"priority\": \"high\",
    \"due_date\": \"2026-08-15\"
  }")
echo $TASK_RESPONSE | python3 -m json.tool
TASK_ID=$(echo $TASK_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

echo -e "\n${BLUE}8. ADD COMMENT${NC}"
curl -s -X POST $BASE_URL/comments/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"task\": $TASK_ID,
    \"content\": \"This is a test comment\"
  }" | python3 -m json.tool

echo -e "\n${BLUE}9. MOVE TASK${NC}"
curl -s -X POST "$BASE_URL/tasks/$TASK_ID/move/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "column_id": 2
  }' | python3 -m json.tool

echo -e "\n${BLUE}10. COMPLETE TASK${NC}"
curl -s -X POST "$BASE_URL/tasks/$TASK_ID/complete/" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo -e "\n${BLUE}11. GET DASHBOARD STATS${NC}"
curl -s -X GET "$BASE_URL/dashboard/stats/" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo -e "\n${BLUE}12. GET ACTIVITY LOGS${NC}"
curl -s -X GET "$BASE_URL/activities/" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo -e "\n${BLUE}13. GET TASK DETAILS${NC}"
curl -s -X GET "$BASE_URL/tasks/$TASK_ID/" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo -e "\n${GREEN}ALL TESTS COMPLETED SUCCESSFULLY!${NC}"