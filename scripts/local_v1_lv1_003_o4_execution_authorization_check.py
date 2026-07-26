"""Validate the fail-closed LV1-003 O4 Attempt 009 one-shot authorization."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

from ithildin_schemas import JsonObject, JsonValue, sha256_digest

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import mission_command_runner_bridge_authorization_check as code_authorization

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = Path("docs/codex/local-v1-lv1-003-o4-execution-authorization.json")
DOCUMENT = Path("docs/codex/local-v1-lv1-003-o4-execution-authorization.md")
PRODUCER_CONTRACT = Path("docs/codex/local-v1-lv1-003-o4-producer-contract.md")
PRODUCER_EXACT_REVIEW = Path("docs/codex/local-v1-lv1-003-o4-producer-exact-review.md")
DISPOSITION_JSON = Path("docs/codex/local-v1-lv1-003-o4-post-review-disposition.json")
DISPOSITION_DOCUMENT = Path("docs/codex/local-v1-lv1-003-o4-post-review-disposition.md")
ATTEMPT_001_DISPOSITION_JSON = Path("docs/codex/local-v1-lv1-003-o4-attempt-001-disposition.json")
ATTEMPT_001_DISPOSITION_DOCUMENT = Path("docs/codex/local-v1-lv1-003-o4-attempt-001-disposition.md")
ENTRYPOINT_REPAIR_REVIEW = Path("docs/codex/local-v1-lv1-003-o4-entrypoint-repair-exact-review.md")
ATTEMPT_002_DISPOSITION_JSON = Path("docs/codex/local-v1-lv1-003-o4-attempt-002-disposition.json")
ATTEMPT_002_DISPOSITION_DOCUMENT = Path("docs/codex/local-v1-lv1-003-o4-attempt-002-disposition.md")
ATTEMPT_002_CLOSURE_JSON = Path("docs/codex/local-v1-lv1-003-o4-attempt-002-closure.json")
ATTEMPT_002_CLOSURE_DOCUMENT = Path("docs/codex/local-v1-lv1-003-o4-attempt-002-closure.md")
COMPOSE_REPAIR_REVIEW = Path("docs/codex/local-v1-lv1-003-o4-compose-repair-exact-review.md")
ATTEMPT_003_DISPOSITION_JSON = Path("docs/codex/local-v1-lv1-003-o4-attempt-003-disposition.json")
ATTEMPT_003_DISPOSITION_DOCUMENT = Path("docs/codex/local-v1-lv1-003-o4-attempt-003-disposition.md")
ATTEMPT_003_CLOSURE_JSON = Path("docs/codex/local-v1-lv1-003-o4-attempt-003-closure.json")
ATTEMPT_003_CLOSURE_DOCUMENT = Path("docs/codex/local-v1-lv1-003-o4-attempt-003-closure.md")
ATTEMPT_004_DISPOSITION_JSON = Path("docs/codex/local-v1-lv1-003-o4-attempt-004-disposition.json")
ATTEMPT_004_DISPOSITION_DOCUMENT = Path("docs/codex/local-v1-lv1-003-o4-attempt-004-disposition.md")
ATTEMPT_005_DISPOSITION_JSON = Path("docs/codex/local-v1-lv1-003-o4-attempt-005-disposition.json")
ATTEMPT_005_DISPOSITION_DOCUMENT = Path("docs/codex/local-v1-lv1-003-o4-attempt-005-disposition.md")
ATTEMPT_006_DISPOSITION_JSON = Path("docs/codex/local-v1-lv1-003-o4-attempt-006-disposition.json")
ATTEMPT_006_DISPOSITION_DOCUMENT = Path("docs/codex/local-v1-lv1-003-o4-attempt-006-disposition.md")
ATTEMPT_007_DISPOSITION_JSON = Path("docs/codex/local-v1-lv1-003-o4-attempt-007-disposition.json")
ATTEMPT_007_DISPOSITION_DOCUMENT = Path("docs/codex/local-v1-lv1-003-o4-attempt-007-disposition.md")
ATTEMPT_008_DISPOSITION_JSON = Path("docs/codex/local-v1-lv1-003-o4-attempt-008-disposition.json")
ATTEMPT_008_DISPOSITION_DOCUMENT = Path("docs/codex/local-v1-lv1-003-o4-attempt-008-disposition.md")
IMAGE_RECOVERY_AUTHORIZATION = Path(
    "docs/codex/local-v1-lv1-003-o4-image-recovery-authorization.json"
)
IMAGE_RECOVERY_AUTHORIZATION_DOCUMENT = Path(
    "docs/codex/local-v1-lv1-003-o4-image-recovery-authorization.md"
)
IMAGE_RECOVERY_CLOSURE = Path("docs/codex/local-v1-lv1-003-o4-image-recovery-closure.json")
IMAGE_RECOVERY_CLOSURE_DOCUMENT = Path("docs/codex/local-v1-lv1-003-o4-image-recovery-closure.md")
RUNTIME_NATIVE_REPAIR_REVIEW = Path(
    "docs/codex/local-v1-lv1-003-o4-runtime-native-repair-exact-review.md"
)
DIAGNOSTIC_REPAIR_REVIEW = Path("docs/codex/local-v1-lv1-003-o4-diagnostic-repair-exact-review.md")
API_CONTAINER_STATE_DIAGNOSTIC_REVIEW = Path(
    "docs/codex/local-v1-lv1-003-o4-api-container-state-diagnostic-exact-review.md"
)
APPLICATION_STARTUP_STAGE_DIAGNOSTIC_REVIEW = Path(
    "docs/codex/local-v1-lv1-003-o4-application-startup-stage-diagnostic-exact-review.md"
)
IMAGE_READABILITY_REPAIR_REVIEW = Path(
    "docs/codex/local-v1-lv1-003-o4-image-readability-repair-exact-review.md"
)
ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REVIEW = Path(
    "docs/codex/local-v1-lv1-003-o4-enrollment-output-projection-repair-exact-review.md"
)
AUTHORIZATION_TARGET = "local-v1-lv1-003-o4-execution-authorization-check"
PRODUCER_STATIC_TARGET = "local-v1-lv1-003-o4-producer-static-check"
PRODUCER_RUN_TARGET = "local-v1-lv1-003-o4-producer-run"
PRODUCER_MODULE_INVOCATION = "uv run python -m scripts.local_v1_lv1_003_o4_producer"
PRODUCER_RUN_COMMENT = (
    "# LIVE, gate-protected entrypoint. Attempt 009 allows one exact supervised invocation."
)
FAILED_FILE_PATH_INVOCATION = "uv run python scripts/local_v1_lv1_003_o4_producer.py"
ENTRYPOINT_REPAIR_BASE_COMMIT = "148effd50c69b40a005f86f6217fc3db8b665a06"
ENTRYPOINT_REPAIR_COMMIT = "88c707f1c90d5807a81412ea7790b3a0b94e2f85"
ENTRYPOINT_REPAIR_TREE = "5316f8f270eb55af38dd032ec7723edef8a423c5"
REVIEWED_IMPLEMENTATION_COMMIT = "5dab3654391c14fe214a9dfe302c099d0fe5fbf8"
REVIEWED_IMPLEMENTATION_TREE = "f9a0cb66ac12e6e0ecca7fc23a0071be0dbe3075"
HISTORICAL_CANDIDATE_PARENT_COMMIT = "86e75f0cf7f92ceb33218f2a66a00668f4da9e12"
HISTORICAL_CANDIDATE_PARENT_TREE = "11d9a752b8e08b483e1d8b9a347a06b5d8bf9af7"
CODE_AUTHORIZATION_COMMIT = HISTORICAL_CANDIDATE_PARENT_COMMIT
CODE_AUTHORIZATION_TREE = HISTORICAL_CANDIDATE_PARENT_TREE
CODE_AUTHORIZATION_ORIGIN_COMMIT = "da17fbc86369ed5a6e7f9de7c1098322bcda4ac9"
CODE_AUTHORIZATION_ORIGIN_TREE = "7e3c14074a568dc47f7363eaab4e8ec4b996982f"
CODE_AUTHORIZATION_RECORD_DIGEST = (
    "sha256:2420d1c22faaec94d15834734b5b2f700579446c9e5fb9ea742855ff78a7b83d"
)
CODE_AUTHORIZATION_ORIGIN_RECORD_DIGEST = (
    "sha256:f241034bc56219c29ecaa215cdbed1404516130b8093567611a8c56960b1a051"
)
HISTORICAL_PRODUCER_CONTRACT_DIGEST = (
    "sha256:3c742762465380387153f5ee17686ed540354926c5364c9e73f15100d9bb30e1"
)
PRODUCER_CONTRACT_DIGEST = "sha256:e972cf112ca0bc659f889cc50d2902d9d68137724e3f4d508bcc8e149d4af18b"
PRODUCER_EXACT_REVIEW_DIGEST = (
    "sha256:5d023bb589636fc991a86768fb97f737cae2cdd58da369c94f99a99d20245c76"
)
DISPOSITION_JSON_DIGEST = "sha256:98671458e5c4053e3a892781dfb53bf8be0d397f578995e80a20483166095593"
DISPOSITION_DOCUMENT_DIGEST = (
    "sha256:9ddd3fc6a78c6556233888a6828e1540b4f85c68660618a424d228bc3b79eea8"
)
ATTEMPT_001_DISPOSITION_JSON_DIGEST = (
    "sha256:16545c118efc7fc93d57534215d1b2defeb920fb9cde388cedd14e646db00671"
)
ATTEMPT_001_DISPOSITION_DOCUMENT_DIGEST = (
    "sha256:3b3e12c7e6f1993c2c256eb0140e15dedf7dc42914cbf67a29de11ed20c7a245"
)
ATTEMPT_001_ID = "LV1-003-O4-ATTEMPT-001"
ATTEMPT_001_CANDIDATE_COMMIT = "9a9e10a083ee9019b58d49d5099040e18bfbb7f2"
ATTEMPT_001_CANDIDATE_TREE = "aa3eecea481dd5c92925ceec3421c051c63cb3cf"
ATTEMPT_001_AUTHORIZATION_CONTRACT_DIGEST = (
    "sha256:2dfd27d564a8359ae66c87bd0ed7308cf74cd2cf5561aa60a80ba04b83bd6863"
)
ATTEMPT_001_COMMAND = "uv run python scripts/local_v1_lv1_003_o4_producer.py"
ENTRYPOINT_REPAIR_REVIEW_DIGEST = (
    "sha256:c3f5260cbdc71b3be22b3bcf1db9e3974718bb3fed5ed5244f3729b0c14e4750"
)
ATTEMPT_002_DISPOSITION_JSON_DIGEST = (
    "sha256:131e421ba479abbb2b68d93f04b6c4ffdb76da94535cf1810a8abca59ba7b7c1"
)
ATTEMPT_002_DISPOSITION_DOCUMENT_DIGEST = (
    "sha256:389a81a2a491ba9d5540e6eba54f18f58459404dd9642e3f47feaeeea0fe6e10"
)
ATTEMPT_002_ID = "LV1-003-O4-ATTEMPT-002"
ATTEMPT_002_OPERATOR_COMMAND = f"make {PRODUCER_RUN_TARGET}"
ATTEMPT_002_CLOSURE_JSON_DIGEST = (
    "sha256:b5cd26f34f2f9df4e7be56284a597ac71e42f187871d1ab2affba508ac3b0cf9"
)
ATTEMPT_002_CLOSURE_DOCUMENT_DIGEST = (
    "sha256:9d94b78873a030ab7f957e6dcd0ba722085abb5a54decd52710941bfa7faa947"
)
ATTEMPT_002_CANDIDATE_COMMIT = "02c78966f9096870e0f8744ba42116bb364ecfcd"
ATTEMPT_002_CANDIDATE_TREE = "a26b90fee43120a0b9a34f09fc4b75f6fcf07e99"
ATTEMPT_002_RUN_ID = "20260725T114755Z-c46245d0"
ATTEMPT_002_PROJECT = "ithildin-local-v1-o4-c46245d0"
COMPOSE_REPAIR_COMMIT = "7e6eb9f0fcad35016f611096543fa4a81017259c"
COMPOSE_REPAIR_TREE = "fef080b85db9b44675150954d6af5afd5d6fec0d"
COMPOSE_REPAIR_REVIEW_DIGEST = (
    "sha256:3209b958f6a7810e753e0c50dccdd113349faf96d6a9b45329d1966924d009dc"
)
COMPOSE_REPAIR_PRODUCER_DIGEST = (
    "sha256:b4d44f09183fca2df5cab33496571c3ac316420074e8eeba71e506fd92999c4b"
)
ATTEMPT_003_DISPOSITION_JSON_DIGEST = (
    "sha256:7ee2abbb5393b3a18904008aebc4f9bbe029bd14358e04611fd8d2966bfb4db9"
)
ATTEMPT_003_DISPOSITION_DOCUMENT_DIGEST = (
    "sha256:dbb437fffc60e6d9796ef88b13a2dd88b9655a265207138314ed0c508cc0a273"
)
ATTEMPT_003_CLOSURE_JSON_DIGEST = (
    "sha256:2dec56200e564decd398fd5c0e1539e60e1c87ebaf453c7093346ca61155db8a"
)
ATTEMPT_003_CLOSURE_DOCUMENT_DIGEST = (
    "sha256:b91cc06f5e88b35a4df18299405c60fa3868303d40c17d900ee101720feffe56"
)
ATTEMPT_003_ID = "LV1-003-O4-ATTEMPT-003"
ATTEMPT_003_CANDIDATE_COMMIT = "7f819bb91c475b4b9fa69b975e629810a7254020"
ATTEMPT_003_CANDIDATE_TREE = "7ff30d4625e6b086809703889376d34cdb0998b5"
ATTEMPT_003_RUN_ID = "20260725T125344Z-6460809b"
ATTEMPT_003_PROJECT = "ithildin-local-v1-o4-6460809b"
IMAGE_RECOVERY_ID = "LV1-003-O4-ATTEMPT-003-IMAGE-RECOVERY-001"
IMAGE_RECOVERY_CANDIDATE_COMMIT = "2051a136e13bacbee4e3fcec332fc4ef78698e73"
IMAGE_RECOVERY_CANDIDATE_TREE = "e0cb7285e720c38a1e071536d7bd25e2bc7caa4e"
IMAGE_RECOVERY_CLOSURE_COMMIT = "bdde370917f11fd9763954a53885d81a4a28b864"
IMAGE_RECOVERY_CLOSURE_TREE = "465de2881a782e30af0696b8bb534161a0336acd"
IMAGE_RECOVERY_AUTHORIZATION_DIGEST = (
    "sha256:103576d2db0b9fe177f935c8e075217c0786a93be34097eca66f906a11faa1aa"
)
IMAGE_RECOVERY_AUTHORIZATION_DOCUMENT_DIGEST = (
    "sha256:7812616aff873ec22426eeb84759889827cbc3fadf98045fc5675b99a0432715"
)
IMAGE_RECOVERY_CLOSURE_DIGEST = (
    "sha256:88a47a8ee15dab08dc508487758564a448cfe4cc9d65c0adce39a2da1fdd8450"
)
IMAGE_RECOVERY_CLOSURE_DOCUMENT_DIGEST = (
    "sha256:69071ab5b0a0c00390726c639d633c0a83e1c93b9fb0c9f91fc835429180a930"
)
RUNTIME_NATIVE_REPAIR_COMMIT = "49db93d80a71855d9ae223826a9849749377c376"
RUNTIME_NATIVE_REPAIR_TREE = "23950855584316daba76acd65be0bfdfd20fbcb9"
RUNTIME_NATIVE_REPAIR_REVIEW_DIGEST = (
    "sha256:635f2e473985f4eef18d541c455ddabb7c09ec782c8c67d37b37da0fbf45e551"
)
RUNTIME_NATIVE_BRIDGE_DIGEST = (
    "sha256:a175feecf1fe08bb1f750fecda51ea57ec17cdfd117f0bb36cddfc7f59bc356e"
)
RUNTIME_NATIVE_PRODUCER_DIGEST = (
    "sha256:d191f58f1b63245499b1447e5e67f21dc638b6a8ad3881a777574c9a7d010f55"
)
ATTEMPT_004_ID = "LV1-003-O4-ATTEMPT-004"
ATTEMPT_004_CANDIDATE_COMMIT = "6452111a1d78f218a24432aaf833004195679318"
ATTEMPT_004_CANDIDATE_TREE = "e8ea86cbd577a2d1323c27b2c3326b3c99ff7804"
ATTEMPT_004_CLOSURE_COMMIT = "1cbef32d467246a2638ed1205de3aea2d6d952d6"
ATTEMPT_004_CLOSURE_TREE = "237d2ff767d7a625b48518e77e8cd7d0d7bec047"
ATTEMPT_004_RUN_ID = "20260725T162319Z-329e129a"
ATTEMPT_004_PROJECT = "ithildin-local-v1-o4-329e129a"
ATTEMPT_004_DISPOSITION_JSON_DIGEST = (
    "sha256:91fd38aceae007d87b0567dc4538370cf4200a1b6f4a7ab6928b219ef15a28c8"
)
ATTEMPT_004_DISPOSITION_DOCUMENT_DIGEST = (
    "sha256:df4d6021f1333e61835ecc5e29b5972f752273910283af21c187665a3bb6cd61"
)
DIAGNOSTIC_REPAIR_COMMIT = "dea1e48acb411e9afd3c6e2c777c05c08e0c5386"
DIAGNOSTIC_REPAIR_TREE = "40e1a7c862b1031dbab1bba9a7f7a30af0beb976"
DIAGNOSTIC_REPAIR_REVIEW_DIGEST = (
    "sha256:f4307fb338c82b6513228641c9437d08c33c948d05b1689102a574b39e60f716"
)
ATTEMPT_005_ID = "LV1-003-O4-ATTEMPT-005"
ATTEMPT_005_CANDIDATE_COMMIT = "affba0570ae15e897f92629966d445ad563ec5ff"
ATTEMPT_005_CANDIDATE_TREE = "8b262e7efa55db72b5402f6924ec938e2d06d85f"
ATTEMPT_005_CLOSURE_COMMIT = "670d97c0294906ca7297eb23bfd28df6f718210d"
ATTEMPT_005_CLOSURE_TREE = "72e480bddada05f21009dd702c8940f3366aebe8"
ATTEMPT_005_RUN_ID = "20260725T172408Z-b806c1bd"
ATTEMPT_005_PROJECT = "ithildin-local-v1-o4-b806c1bd"
ATTEMPT_005_DISPOSITION_JSON_DIGEST = (
    "sha256:58b0791858ff96469fa1ea103358ab60d3167cb4bcf50f62e68f73f4d9258a61"
)
ATTEMPT_005_DISPOSITION_DOCUMENT_DIGEST = (
    "sha256:829355ea19705fb0aa01e1fbf3f9e3933f7541b8eb5da4758ccf9e869432533c"
)
API_CONTAINER_STATE_DIAGNOSTIC_REJECTED_001_COMMIT = "77356340bbabbbedff658abba70800a823f3c1ec"
API_CONTAINER_STATE_DIAGNOSTIC_REJECTED_001_TREE = "4e9f5effd40ea8666df17bb6d57b6a897eafc19d"
API_CONTAINER_STATE_DIAGNOSTIC_REJECTED_002_COMMIT = "01a38cee52a1d9eb73e21bfeed8a047dd56a07c6"
API_CONTAINER_STATE_DIAGNOSTIC_REJECTED_002_TREE = "00f408ed329e0bdb7cae341161a66b4563984dc6"
API_CONTAINER_STATE_DIAGNOSTIC_COMMIT = "3f207b8f390742b956ed62cea674b0e5c557b514"
API_CONTAINER_STATE_DIAGNOSTIC_TREE = "e3bc1d84ab798e34b297b659fa4698003f3423fe"
API_CONTAINER_STATE_DIAGNOSTIC_REVIEW_DIGEST = (
    "sha256:561411e152df0f8f49210ec3380fd39df138a170053c99d48a315a34d498a8d2"
)
API_CONTAINER_STATE_DIAGNOSTIC_PRODUCER_DIGEST = (
    "sha256:412b10a4216add1f999f6c1b09e89c29b901512647e9a0c2537bd571a84948be"
)
API_CONTAINER_STATE_DIAGNOSTIC_TEST_DIGEST = (
    "sha256:1899f3fd2af0b1b9613095d6e35e1d77f55e94f094b46c53206ef17050c56b03"
)
ATTEMPT_006_ID = "LV1-003-O4-ATTEMPT-006"
ATTEMPT_006_CANDIDATE_COMMIT = "d4c1d322a9d3faf24422009b7bc40f73544250af"
ATTEMPT_006_CANDIDATE_TREE = "9acbfc6ee270613518c4c5cc74b2719604946c46"
ATTEMPT_006_CLOSURE_COMMIT = "046356d7eb4b6d92958d9daf9d68d8f714c164b3"
ATTEMPT_006_CLOSURE_TREE = "b9b2c0426eba6e728fd195d79573ee85780aeb5d"
ATTEMPT_006_RUN_ID = "20260725T183846Z-b00570b3"
ATTEMPT_006_PROJECT = "ithildin-local-v1-o4-b00570b3"
ATTEMPT_006_DISPOSITION_JSON_DIGEST = (
    "sha256:8165435a9aaf608746794e48f246cb1c707330eaa291318f6191a6f63e35189c"
)
ATTEMPT_006_DISPOSITION_DOCUMENT_DIGEST = (
    "sha256:d365c60f7b1ab85175d0983033836ecb44298adbfd25d5fdbf95eda48556ff2f"
)
APPLICATION_STARTUP_STAGE_DIAGNOSTIC_COMMIT = "cce80b5cc71e9387237d18b588d294c39351a362"
APPLICATION_STARTUP_STAGE_DIAGNOSTIC_TREE = "4701443cd266cd86d6654a295f6277caddc117f2"
APPLICATION_STARTUP_STAGE_DIAGNOSTIC_REVIEW_DIGEST = (
    "sha256:4d14b14e6fe881b0d1d5487ed7d4e2a84dd671520e7e7c917e7e9e525e6e76b4"
)
APPLICATION_STARTUP_STAGE_PATH_DIGESTS: JsonObject = {
    "apps/api/src/ithildin_api/app.py": (
        "sha256:be8ad59f62dc71180e327ad044c481a4c916cbc42d043bfd88d749d4fbf30730"
    ),
    "apps/api/verified_launch.py": (
        "sha256:9c7a71bcc9c4643e203a578486b04ea392df1985b99b0da06a89973b20a96408"
    ),
    "scripts/local_v1_lv1_003_o4_producer.py": (
        "sha256:76f74c3c2b75ae8b320c5c12c3087b51a714ec1f9230a373a3d9335e9df0aca0"
    ),
    "tests/test_api_service.py": (
        "sha256:4c74e040294ccf216436bd729ab5f84536912d7cd17d5a3d587a57c7c5a69d2c"
    ),
    "tests/test_local_v1_lv1_003_o4_producer.py": (
        "sha256:d7f0df7e818c43d83abe42b4e1c5d9d97e4fa05d8a7ef64927549a511d9f3a45"
    ),
    "tests/test_runtime_candidate_bootstrap.py": (
        "sha256:68cdceb283d5968ede0d589d46b96e0a9319bffd83a037105320ec4a21139896"
    ),
}
ATTEMPT_007_ID = "LV1-003-O4-ATTEMPT-007"
ATTEMPT_007_CANDIDATE_COMMIT = "a2f0338a045dd15352c77cb1841f2098013b1f86"
ATTEMPT_007_CANDIDATE_TREE = "04a5dbe34b604c95eb5a63bbfc9610b1033bf521"
ATTEMPT_007_RUN_ID = "20260725T194808Z-1993a10f"
ATTEMPT_007_PROJECT = "ithildin-local-v1-o4-1993a10f"
ATTEMPT_007_DISPOSITION_JSON_DIGEST = (
    "sha256:e493458d984c823c6690ef649745c18ba0082ab4494eaff9c3fa62a82685b3a7"
)
ATTEMPT_007_DISPOSITION_DOCUMENT_DIGEST = (
    "sha256:8f842dc22c7520bdac5f40636a10197eb712ccd0041687a9cf5a18d5b59aaf72"
)
IMAGE_READABILITY_REPAIR_BASE_COMMIT = "fbd2da4f26b24c9b1aa7fad4336eb99c5ccf9491"
IMAGE_READABILITY_REPAIR_COMMIT = "7cc1da575074895a7210c5f15a34ae136f4f932a"
IMAGE_READABILITY_REPAIR_TREE = "b448eb922619e59af74275cf1070deb33b6813ef"
IMAGE_READABILITY_REPAIR_REVIEW_DIGEST = (
    "sha256:3d95c58d0c50d1ae229f0484b3a27cabfaee8d181f39b3285772b54384d0b423"
)
IMAGE_READABILITY_REPAIR_PATH_DIGESTS: JsonObject = {
    "deploy/Dockerfile.api": (
        "sha256:b0fba85ea070c8d2100d79b69db202f2a2ef35adae4e2497c3f0fe320341744a"
    ),
    "deploy/Dockerfile.node": (
        "sha256:28f989781bcfce6373a6eff8d13e68334f742c528c35c42a7463fcf01edadd21"
    ),
    "deploy/Dockerfile.ui": (
        "sha256:e562a3721c9750b747820f79b77c6d554be1d096d1f6a4dd0d371d83ce1aaa0a"
    ),
    "deploy/hermes-node-bridge/Dockerfile": (
        "sha256:82d992e42fa471cea5bbbd92c28d593e17368561f4442ed518cf53b148c6ca5d"
    ),
    "tests/test_container_image_runtime_readability.py": (
        "sha256:43295b57b2d7e368c5f6e735e812bc61349687aa84ee05b788a559fad9aab056"
    ),
}
ATTEMPT_008_ID = "LV1-003-O4-ATTEMPT-008"
ATTEMPT_008_CANDIDATE_COMMIT = "ae6824bd6d81f58efc5a3383d63341d20ae3467a"
ATTEMPT_008_CANDIDATE_TREE = "8e5a0d45369ca559e271aa3fd58c19e6bb57e33c"
ATTEMPT_008_RUN_ID = "20260726T001909Z-d801f37b"
ATTEMPT_008_PROJECT = "ithildin-local-v1-o4-d801f37b"
ATTEMPT_008_DISPOSITION_JSON_DIGEST = (
    "sha256:5ba9f74000174d7498feedc0c5f1d9acc8538ab5d34416d19650f8efc5bceb62"
)
ATTEMPT_008_DISPOSITION_DOCUMENT_DIGEST = (
    "sha256:6d993a2bfa41b649cb3eb78fe6b659edb8ec066dc8d5857a860627bdd21a5b7e"
)
ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REJECTED_COMMIT = "dd96e47adba2baf49b890d821098e326bad93f84"
ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REJECTED_TREE = "9e57f240ac65ffad38a66387648836bd1afdc489"
ENROLLMENT_OUTPUT_PROJECTION_REPAIR_BASE_COMMIT = "6fcea4cad23c051abfbf09227948328975ccf724"
ENROLLMENT_OUTPUT_PROJECTION_REPAIR_COMMIT = "8cd307e3ce2ca20e6fdc1b53fc1937bfa5568685"
ENROLLMENT_OUTPUT_PROJECTION_REPAIR_TREE = "4dacc4015a51d61b29dc3e089900b2e12ab1d7b6"
ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REVIEW_DIGEST = (
    "sha256:79c6ca4354895005c499b1bea8c62e03001fdc63d8a1b5c376f8c956a71005a0"
)
ENROLLMENT_OUTPUT_PROJECTION_REPAIR_PATH_DIGESTS: JsonObject = {
    "apps/node/src/ithildin_node/__main__.py": (
        "sha256:b7b3e9988f9351b25f24cf000f424bce1390cbb6be3010c41dce767987ac358d"
    ),
    "docs/codex/local-v1-lv1-003-o4-producer-contract.md": (
        "sha256:e972cf112ca0bc659f889cc50d2902d9d68137724e3f4d508bcc8e149d4af18b"
    ),
    "scripts/local_v1_lv1_003_o4_producer.py": (
        "sha256:cd5be3b081afda05a93ef29013a8d67bbac683d0f4118b77111939396c490bd4"
    ),
    "tests/test_local_v1_lv1_003_o4_producer.py": (
        "sha256:299fe6d8c5dbf1de2ebcdef1f745223d460b649312ad693a34bf7133a82c59d7"
    ),
    "tests/test_node_cli.py": (
        "sha256:8446ca4b6328d395cb93018ff765961a1ba81b9a5e2e7f5b690f712306abd100"
    ),
}
ENROLLMENT_OUTPUT_PROJECTION_REPAIR_PATHS = list(ENROLLMENT_OUTPUT_PROJECTION_REPAIR_PATH_DIGESTS)
ATTEMPT_009_ID = "LV1-003-O4-ATTEMPT-009"
CANDIDATE_PARENT_COMMIT = ENROLLMENT_OUTPUT_PROJECTION_REPAIR_COMMIT
CANDIDATE_PARENT_TREE = ENROLLMENT_OUTPUT_PROJECTION_REPAIR_TREE
ATTEMPT_002_RECEIPT_BASE = Path("var/local-v1-lv1-003-o4-receipts")
ATTEMPT_002_RECEIPT_ROOT = ATTEMPT_002_RECEIPT_BASE / ATTEMPT_002_RUN_ID
ATTEMPT_002_DISPOSITION_RECEIPT = ATTEMPT_002_RECEIPT_ROOT / "disposition.json"
ATTEMPT_002_MANIFEST_RECEIPT = ATTEMPT_002_RECEIPT_ROOT / "candidate-manifest.json"
ATTEMPT_002_SNAPSHOT_ROOT = ATTEMPT_002_RECEIPT_ROOT / "candidate"
ATTEMPT_002_RUNTIME_BASE = Path("var/local-v1-lv1-003-o4-runtime")
ATTEMPT_002_RUNTIME_ROOT = ATTEMPT_002_RUNTIME_BASE / ATTEMPT_002_RUN_ID
ATTEMPT_002_REPORT_BASE = Path("var/local-v1-constrained-mission-journey")
ATTEMPT_002_REPORT_ROOT = ATTEMPT_002_REPORT_BASE / ATTEMPT_002_RUN_ID
ATTEMPT_002_DISPOSITION_BYTES = (
    b'{"failure_code":"fixed_compose_invalid","release_allowed":false,'
    b'"status":"quarantined_not_published","uat_complete":false}\n'
)
ATTEMPT_002_DISPOSITION_RECEIPT_DIGEST = (
    "sha256:653e7cb4a656db714769cad329b49c55a194bb5223c911274a57c4a7abbef44b"
)
ATTEMPT_002_MANIFEST_RECEIPT_DIGEST = (
    "sha256:ac9a119a083a786cfcead9cd5600a43350bc78cd2f500ffcc59f4969e34f087b"
)
ATTEMPT_002_MANIFEST_SIZE = 96628
ATTEMPT_002_SNAPSHOT_FILE_COUNT = 663
ATTEMPT_003_RECEIPT_ROOT = ATTEMPT_002_RECEIPT_BASE / ATTEMPT_003_RUN_ID
ATTEMPT_003_DISPOSITION_RECEIPT = ATTEMPT_003_RECEIPT_ROOT / "disposition.json"
ATTEMPT_003_MANIFEST_RECEIPT = ATTEMPT_003_RECEIPT_ROOT / "candidate-manifest.json"
ATTEMPT_003_SNAPSHOT_ROOT = ATTEMPT_003_RECEIPT_ROOT / "candidate"
ATTEMPT_003_RUNTIME_ROOT = ATTEMPT_002_RUNTIME_BASE / ATTEMPT_003_RUN_ID
ATTEMPT_004_RECEIPT_ROOT = ATTEMPT_002_RECEIPT_BASE / ATTEMPT_004_RUN_ID
ATTEMPT_004_RUNTIME_ROOT = ATTEMPT_002_RUNTIME_BASE / ATTEMPT_004_RUN_ID
ATTEMPT_005_RECEIPT_ROOT = ATTEMPT_002_RECEIPT_BASE / ATTEMPT_005_RUN_ID
ATTEMPT_005_RUNTIME_ROOT = ATTEMPT_002_RUNTIME_BASE / ATTEMPT_005_RUN_ID
ATTEMPT_006_RECEIPT_ROOT = ATTEMPT_002_RECEIPT_BASE / ATTEMPT_006_RUN_ID
ATTEMPT_006_RUNTIME_ROOT = ATTEMPT_002_RUNTIME_BASE / ATTEMPT_006_RUN_ID
ATTEMPT_007_RECEIPT_ROOT = ATTEMPT_002_RECEIPT_BASE / ATTEMPT_007_RUN_ID
ATTEMPT_007_RUNTIME_ROOT = ATTEMPT_002_RUNTIME_BASE / ATTEMPT_007_RUN_ID
ATTEMPT_008_RECEIPT_ROOT = ATTEMPT_002_RECEIPT_BASE / ATTEMPT_008_RUN_ID
ATTEMPT_008_RUNTIME_ROOT = ATTEMPT_002_RUNTIME_BASE / ATTEMPT_008_RUN_ID
IMAGE_RECOVERY_CONSUMPTION_RECEIPT_NAME = "attempt-003-image-recovery-001-consumed.json"
IMAGE_RECOVERY_CONSUMPTION_RECEIPT = (
    ATTEMPT_002_RUNTIME_BASE / IMAGE_RECOVERY_CONSUMPTION_RECEIPT_NAME
)
IMAGE_RECOVERY_CONSUMPTION_RECEIPT_BYTES = (
    b'{"candidate_commit":"2051a136e13bacbee4e3fcec332fc4ef78698e73",'
    b'"candidate_tree":"e0cb7285e720c38a1e071536d7bd25e2bc7caa4e",'
    b'"record_type":"local_v1_lv1_003_o4_image_recovery_consumption",'
    b'"recovery_id":"LV1-003-O4-ATTEMPT-003-IMAGE-RECOVERY-001",'
    b'"retry_authorized":false,"schema_version":"1",'
    b'"status":"consumed_before_docker_inspection"}\n'
)
IMAGE_RECOVERY_CONSUMPTION_RECEIPT_DIGEST = (
    "sha256:df7ce1a69c5fc3b27011f788f846bb5b385ed6f3d348ceb6c78d12de9366ca3c"
)
ATTEMPT_003_DISPOSITION_BYTES = (
    b'{"failure_code":"recovery_required","release_allowed":false,'
    b'"status":"quarantined_not_published","uat_complete":false}\n'
)
ATTEMPT_003_DISPOSITION_RECEIPT_DIGEST = (
    "sha256:03bceb292828f68440c2183438f856edd4b291130d6f276b9418a3d2ad967992"
)
ATTEMPT_003_MANIFEST_RECEIPT_DIGEST = (
    "sha256:ed011c2f54edde19a959f85e77c575aa57e47094c99f15473faecf9d1190df96"
)
ATTEMPT_003_MANIFEST_SIZE = 96628
ATTEMPT_003_SNAPSHOT_FILE_COUNT = 663
ATTEMPT_004_DISPOSITION_RECEIPT_DIGEST = (
    "sha256:03bceb292828f68440c2183438f856edd4b291130d6f276b9418a3d2ad967992"
)
ATTEMPT_004_DIAGNOSTIC_RECEIPT_DIGEST = (
    "sha256:dcff6467ffa83cad6f9b86d4e9883d7206b76fa5f2f8407f5d8f765284eac3e6"
)
ATTEMPT_004_DIAGNOSTIC_SIZE = 6885
ATTEMPT_004_MANIFEST_RECEIPT_DIGEST = (
    "sha256:4e1256eba744acb3d1dbcef123cdf04e57d801c89cf83a4754448739234ff534"
)
ATTEMPT_004_MANIFEST_SIZE = 96772
ATTEMPT_004_SNAPSHOT_FILE_COUNT = 664
ATTEMPT_005_DISPOSITION_BYTES = (
    b'{"failure_code":"base_services_start_failed","release_allowed":false,'
    b'"status":"quarantined_not_published","uat_complete":false}\n'
)
ATTEMPT_005_DISPOSITION_RECEIPT_DIGEST = (
    "sha256:5a84070039cc153416cf6fcc3a12c9f13bbd921befa97ee4b33a861a309b9d7a"
)
ATTEMPT_005_DIAGNOSTIC_RECEIPT_DIGEST = (
    "sha256:e4064aacddd05b2e835fcb7064ace5b88be1e3dab8328a7ebb888da899114738"
)
ATTEMPT_005_DIAGNOSTIC_SIZE = 7059
ATTEMPT_005_MANIFEST_RECEIPT_DIGEST = (
    "sha256:dddff25f5969763100f54963dfba8f3f1d74ee16f6bc5ef580d4797ae6a75a0f"
)
ATTEMPT_005_MANIFEST_SIZE = 96772
ATTEMPT_005_SNAPSHOT_FILE_COUNT = 664
ATTEMPT_006_DISPOSITION_BYTES = (
    b'{"failure_code":"base_services_start_failed","release_allowed":false,'
    b'"status":"quarantined_not_published","uat_complete":false}\n'
)
ATTEMPT_006_DISPOSITION_RECEIPT_DIGEST = (
    "sha256:5a84070039cc153416cf6fcc3a12c9f13bbd921befa97ee4b33a861a309b9d7a"
)
ATTEMPT_006_DIAGNOSTIC_RECEIPT_DIGEST = (
    "sha256:5203fad9e028b6596c46358de00ab5a24e78ab314dbb582f9c3184ad4ac296b5"
)
ATTEMPT_006_DIAGNOSTIC_SIZE = 7270
ATTEMPT_006_MANIFEST_RECEIPT_DIGEST = (
    "sha256:001e9c51992339079de8560d372a463ce7b30b4d9ff1be38cd516e7148f78fcd"
)
ATTEMPT_006_MANIFEST_SIZE = 96772
ATTEMPT_006_SNAPSHOT_FILE_COUNT = 664
ATTEMPT_007_DISPOSITION_BYTES = ATTEMPT_006_DISPOSITION_BYTES
ATTEMPT_007_DISPOSITION_RECEIPT_DIGEST = ATTEMPT_006_DISPOSITION_RECEIPT_DIGEST
ATTEMPT_007_DIAGNOSTIC_RECEIPT_DIGEST = (
    "sha256:add06ef7d609b220e52d3ab0053a8521262d1dbc253b0d972cae83442f97cf10"
)
ATTEMPT_007_DIAGNOSTIC_SIZE = 7438
ATTEMPT_007_MANIFEST_RECEIPT_DIGEST = (
    "sha256:73219848ccef6715ee7c1f3fb5356ecced8db36eea58bc449cf64d37e7197998"
)
ATTEMPT_007_MANIFEST_SIZE = 96772
ATTEMPT_007_SNAPSHOT_FILE_COUNT = 664
ATTEMPT_008_DISPOSITION_BYTES = ATTEMPT_003_DISPOSITION_BYTES
ATTEMPT_008_DISPOSITION_RECEIPT_DIGEST = ATTEMPT_003_DISPOSITION_RECEIPT_DIGEST
ATTEMPT_008_DIAGNOSTIC_RECEIPT_DIGEST = (
    "sha256:cf303eb045cf522e62c5fa5b2f35fc54d5ecd5981e1c0c1428d4584d6a165b28"
)
ATTEMPT_008_DIAGNOSTIC_SIZE = 7174
ATTEMPT_008_MANIFEST_RECEIPT_DIGEST = (
    "sha256:04d64359cbc275181d90b50cef3534c550a0d7e446ae12caee3f5fe7bcb19c54"
)
ATTEMPT_008_MANIFEST_SIZE = 96772
ATTEMPT_008_SNAPSHOT_FILE_COUNT = 664
MAX_RETAINED_SNAPSHOT_FILE_BYTES = 16 * 1_048_576
MAX_RETAINED_SNAPSHOT_BYTES = 64 * 1_048_576
EVIDENCE_IGNORE_PATTERNS = [
    "var/local-v1-lv1-003-o4-receipts/*",
    "var/local-v1-lv1-003-o4-runtime/*",
    "var/local-v1-constrained-mission-journey/*",
]
CLOSURE_CONTROL_PATH_ALLOWLIST = [
    ".gitignore",
    ATTEMPT_002_CLOSURE_JSON.as_posix(),
    ATTEMPT_002_CLOSURE_DOCUMENT.as_posix(),
    CONTRACT.as_posix(),
    DOCUMENT.as_posix(),
    "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
    "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
]
HISTORICAL_CONTROL_PATH_ALLOWLIST = [
    CONTRACT.as_posix(),
    DOCUMENT.as_posix(),
    DISPOSITION_JSON.as_posix(),
    DISPOSITION_DOCUMENT.as_posix(),
    "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
    "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
]
CONTROL_PATH_ALLOWLIST = [
    ATTEMPT_002_DISPOSITION_JSON.as_posix(),
    ATTEMPT_002_DISPOSITION_DOCUMENT.as_posix(),
    ENTRYPOINT_REPAIR_REVIEW.as_posix(),
    CONTRACT.as_posix(),
    DOCUMENT.as_posix(),
    "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
    "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
]
ATTEMPT_003_CONTROL_PATH_ALLOWLIST = [
    ATTEMPT_003_DISPOSITION_JSON.as_posix(),
    ATTEMPT_003_DISPOSITION_DOCUMENT.as_posix(),
    COMPOSE_REPAIR_REVIEW.as_posix(),
    CONTRACT.as_posix(),
    DOCUMENT.as_posix(),
    "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
    "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
]
ATTEMPT_003_CLOSURE_CONTROL_PATH_ALLOWLIST = [
    ATTEMPT_003_CLOSURE_JSON.as_posix(),
    ATTEMPT_003_CLOSURE_DOCUMENT.as_posix(),
    CONTRACT.as_posix(),
    DOCUMENT.as_posix(),
    "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
    "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
]
ATTEMPT_004_CONTROL_PATH_ALLOWLIST = [
    "Makefile",
    "README.md",
    CONTRACT.as_posix(),
    DOCUMENT.as_posix(),
    RUNTIME_NATIVE_REPAIR_REVIEW.as_posix(),
    "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
    "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
]
ATTEMPT_004_CLOSURE_CONTROL_PATH_ALLOWLIST = [
    "Makefile",
    "README.md",
    ATTEMPT_004_DISPOSITION_JSON.as_posix(),
    ATTEMPT_004_DISPOSITION_DOCUMENT.as_posix(),
    CONTRACT.as_posix(),
    DOCUMENT.as_posix(),
    "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
    "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
]
ATTEMPT_005_CONTROL_PATH_ALLOWLIST = [
    "Makefile",
    "README.md",
    DIAGNOSTIC_REPAIR_REVIEW.as_posix(),
    CONTRACT.as_posix(),
    DOCUMENT.as_posix(),
    "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
    "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
]
ATTEMPT_005_CLOSURE_CONTROL_PATH_ALLOWLIST = [
    "Makefile",
    "README.md",
    ATTEMPT_005_DISPOSITION_JSON.as_posix(),
    ATTEMPT_005_DISPOSITION_DOCUMENT.as_posix(),
    CONTRACT.as_posix(),
    DOCUMENT.as_posix(),
    "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
    "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
]
ATTEMPT_006_CONTROL_PATH_ALLOWLIST = [
    "Makefile",
    "README.md",
    API_CONTAINER_STATE_DIAGNOSTIC_REVIEW.as_posix(),
    CONTRACT.as_posix(),
    DOCUMENT.as_posix(),
    "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
    "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
]
ATTEMPT_006_CLOSURE_CONTROL_PATH_ALLOWLIST = [
    "Makefile",
    "README.md",
    ATTEMPT_006_DISPOSITION_JSON.as_posix(),
    ATTEMPT_006_DISPOSITION_DOCUMENT.as_posix(),
    CONTRACT.as_posix(),
    DOCUMENT.as_posix(),
    "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
    "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
]
ATTEMPT_007_CONTROL_PATH_ALLOWLIST = [
    "Makefile",
    "README.md",
    APPLICATION_STARTUP_STAGE_DIAGNOSTIC_REVIEW.as_posix(),
    CONTRACT.as_posix(),
    DOCUMENT.as_posix(),
    "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
    "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
]
ATTEMPT_007_CLOSURE_CONTROL_PATH_ALLOWLIST = [
    "Makefile",
    "README.md",
    ATTEMPT_007_DISPOSITION_JSON.as_posix(),
    ATTEMPT_007_DISPOSITION_DOCUMENT.as_posix(),
    CONTRACT.as_posix(),
    DOCUMENT.as_posix(),
    "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
    "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
]
ATTEMPT_008_CONTROL_PATH_ALLOWLIST = [
    "Makefile",
    "README.md",
    CONTRACT.as_posix(),
    DOCUMENT.as_posix(),
    IMAGE_READABILITY_REPAIR_REVIEW.as_posix(),
    "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
    "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
]
ATTEMPT_008_CLOSURE_CONTROL_PATH_ALLOWLIST = [
    "Makefile",
    "README.md",
    ATTEMPT_008_DISPOSITION_JSON.as_posix(),
    ATTEMPT_008_DISPOSITION_DOCUMENT.as_posix(),
    CONTRACT.as_posix(),
    DOCUMENT.as_posix(),
    "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
    "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
]
ATTEMPT_009_CONTROL_PATH_ALLOWLIST = [
    "Makefile",
    "README.md",
    ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REVIEW.as_posix(),
    CONTRACT.as_posix(),
    DOCUMENT.as_posix(),
    "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
    "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
]
IMAGE_READABILITY_REPAIR_PATHS = list(IMAGE_READABILITY_REPAIR_PATH_DIGESTS)
APPLICATION_STARTUP_STAGE_DIAGNOSTIC_PATHS = list(APPLICATION_STARTUP_STAGE_PATH_DIGESTS)
DIAGNOSTIC_REPAIR_PATHS = [
    "scripts/local_v1_lv1_003_o4_producer.py",
    "tests/test_local_v1_lv1_003_o4_producer.py",
]
API_CONTAINER_STATE_DIAGNOSTIC_PATHS = [
    "scripts/local_v1_lv1_003_o4_producer.py",
    "tests/test_local_v1_lv1_003_o4_producer.py",
]
PRIOR_ATTEMPT_ROOTS = [
    "var/local-v1-lv1-003-o4-receipts",
    "var/local-v1-lv1-003-o4-runtime",
    "var/local-v1-constrained-mission-journey",
]
PROFILE_DIGEST = "sha256:90b94d725640768f1a7d665e979bbe11f263a4ff264591a5348d0b5820db3e92"
SOURCE_DIGESTS = {
    "profile_file_sha256": (
        Path("deploy/hermes-node-bridge/profile.json"),
        "sha256:d39fcb373377ff97d18eb7a81f00157e17baabf134b65231a4c3b20a7370d47e",
    ),
    "base_compose_sha256": (
        Path("deploy/docker-compose.yml"),
        "sha256:895107a268169790024c07fe00556fb5d6df0ce4479f49cbe091ccfc517ceb04",
    ),
    "overlay_compose_sha256": (
        Path("deploy/hermes-node-bridge/compose.yaml"),
        "sha256:f6a78f705165354e9908c4512ab551f87dd16cada6e415d59979d78d6f66107c",
    ),
    "producer_source_sha256": (
        Path("scripts/local_v1_lv1_003_o4_producer.py"),
        cast(
            str,
            ENROLLMENT_OUTPUT_PROJECTION_REPAIR_PATH_DIGESTS[
                "scripts/local_v1_lv1_003_o4_producer.py"
            ],
        ),
    ),
    "producer_test_sha256": (
        Path("tests/test_local_v1_lv1_003_o4_producer.py"),
        cast(
            str,
            ENROLLMENT_OUTPUT_PROJECTION_REPAIR_PATH_DIGESTS[
                "tests/test_local_v1_lv1_003_o4_producer.py"
            ],
        ),
    ),
    "bridge_dockerfile_sha256": (
        Path("deploy/hermes-node-bridge/Dockerfile"),
        cast(
            str,
            IMAGE_READABILITY_REPAIR_PATH_DIGESTS["deploy/hermes-node-bridge/Dockerfile"],
        ),
    ),
    "dependency_lock_sha256": (
        Path("uv.lock"),
        "sha256:a0ea98764d069193226a9debe837f37655ee707cb17dcdf6731b922883a4dafb",
    ),
}
FIXED_ACTIONS = [
    "docker_daemon_version",
    "docker_compose_version",
    "merged_compose_config_quiet",
    "build_base_api_ui_node",
    "build_fixed_hermes_bridge_with_runtime_native_python",
    "bind_and_inspect_owned_image_ids_platform_config_layers_and_labels",
    "start_base_api_ui",
    "collect_bounded_base_service_start_diagnostic_on_start_failure",
    "collect_bounded_api_container_state_diagnostic_after_api_nonzero_exit",
    "collect_closed_application_startup_stage_after_exact_api_application_exit",
    "enroll_node_once_via_stdin",
    "start_ordinary_node",
    "stop_ordinary_node",
    "start_reviewed_fixed_node_wait",
    "run_hermes_once_no_arguments_devnull_output",
    "copy_closed_node_mission_receipt",
    "stop_fixed_node",
    "compose_down_remove_orphans_volumes",
    "list_project_containers_volumes_networks",
    "write_bounded_stable_diagnostic_receipt_on_failure",
    "remove_exact_bound_owned_image_ids",
    "prove_exact_bound_owned_image_ids_and_references_absent",
]
EXTERNAL_PREFLIGHT = [
    "clean_exact_candidate_matching_post_review_disposition",
    "local_docker_socket_uniquely_proven",
    "ambient_docker_host_context_config_credentials_and_proxies_absent",
    "docker_daemon_and_compose_available",
    "ports_8000_and_5173_available",
    "host_local_ollama_reachable_at_127_0_0_1_11434",
    "host_local_ollama_model_inventory_contains_exact_gemma4_e4b",
    "reviewed_hermes_platform_digest_available",
    "isolated_0700_runtime_and_0600_secret_files",
    "source_profile_and_compose_digests_exact",
]
AUTHORITY_FIELDS = {
    "producer_code_authorized",
    "docker_lifecycle_authorized",
    "live_hermes_execution_authorized",
    "model_provider_access_authorized",
    "o4_evidence_execution_authorized",
    "credential_custody_authorized",
    "runner_lifecycle_authority",
    "arbitrary_host_control_authorized",
    "generic_process_control_authorized",
    "shell_execution_authorized",
    "docker_socket_authorized",
    "network_non_bypass_claimed",
    "filesystem_non_bypass_claimed",
    "new_governed_power_authorized",
    "new_governed_tool",
    "release_allowed",
    "promotion_allowed",
    "production_authorized",
    "uat_complete",
}
TOP_LEVEL_FIELDS = {
    "schema_version",
    "record_type",
    "record_status",
    "ticket_id",
    "outcome_id",
    "producer_contract_path",
    "producer_contract_sha256",
    "candidate_parent_commit",
    "candidate_parent_tree",
    "historical_post_review_candidate_parent_commit",
    "historical_post_review_candidate_parent_tree",
    "reviewed_implementation_commit",
    "reviewed_implementation_tree",
    "producer_exact_review_record",
    "producer_exact_review_sha256",
    "code_authorization_origin_commit",
    "code_authorization_origin_tree",
    "code_authorization_commit",
    "code_authorization_tree",
    "code_authorization_origin_record_sha256",
    "code_authorization_record_sha256",
    "post_review_disposition_json",
    "post_review_disposition_json_sha256",
    "post_review_disposition_document",
    "post_review_disposition_document_sha256",
    "attempt_001_disposition_json",
    "attempt_001_disposition_json_sha256",
    "attempt_001_disposition_document",
    "attempt_001_disposition_document_sha256",
    "attempt_001_id",
    "attempt_001_attempted_candidate_commit",
    "attempt_001_attempted_candidate_tree",
    "attempt_001_attempted_authorization_contract_sha256",
    "attempt_001_invocation",
    "attempt_001_root_absence",
    "producer_entrypoint_repair",
    "entrypoint_repair_review_record",
    "entrypoint_repair_review_sha256",
    "attempt_002_disposition_json",
    "attempt_002_disposition_json_sha256",
    "attempt_002_disposition_document",
    "attempt_002_disposition_document_sha256",
    "attempt_002_closure_json",
    "attempt_002_closure_json_sha256",
    "attempt_002_closure_document",
    "attempt_002_closure_document_sha256",
    "compose_repair_review_record",
    "compose_repair_review_sha256",
    "attempt_003_disposition_json",
    "attempt_003_disposition_json_sha256",
    "attempt_003_disposition_document",
    "attempt_003_disposition_document_sha256",
    "attempt_003_closure_json",
    "attempt_003_closure_json_sha256",
    "attempt_003_closure_document",
    "attempt_003_closure_document_sha256",
    "attempt_003_id",
    "attempt_003_candidate_parent_commit",
    "attempt_003_candidate_parent_tree",
    "attempt_003_operator_command",
    "attempt_003_module_command",
    "attempt_003_attempted_candidate_commit",
    "attempt_003_attempted_candidate_tree",
    "attempt_003_failure_code",
    "attempt_003_run_id",
    "attempt_003_compose_project",
    "attempt_003_execution_authorized",
    "attempt_003_automatic_retry_authorized",
    "attempt_003_recovery_authorized",
    "image_recovery_authorization_json",
    "image_recovery_authorization_json_sha256",
    "image_recovery_authorization_document",
    "image_recovery_authorization_document_sha256",
    "image_recovery_closure_json",
    "image_recovery_closure_json_sha256",
    "image_recovery_closure_document",
    "image_recovery_closure_document_sha256",
    "image_recovery_history",
    "runtime_native_repair_review_record",
    "runtime_native_repair_review_sha256",
    "runtime_native_repair_commit",
    "runtime_native_repair_tree",
    "attempt_004_id",
    "attempt_004_candidate_parent_commit",
    "attempt_004_candidate_parent_tree",
    "attempt_004_operator_command",
    "attempt_004_module_command",
    "attempt_004_attempted_candidate_commit",
    "attempt_004_attempted_candidate_tree",
    "attempt_004_failure_code",
    "attempt_004_primary_failure_code",
    "attempt_004_cleanup_failure_codes",
    "attempt_004_run_id",
    "attempt_004_compose_project",
    "attempt_004_disposition_json",
    "attempt_004_disposition_json_sha256",
    "attempt_004_disposition_document",
    "attempt_004_disposition_document_sha256",
    "attempt_004_closure_commit",
    "attempt_004_closure_tree",
    "attempt_004_execution_authorized",
    "attempt_004_automatic_retry_authorized",
    "diagnostic_repair_review_record",
    "diagnostic_repair_review_sha256",
    "diagnostic_repair_commit",
    "diagnostic_repair_tree",
    "attempt_005_id",
    "attempt_005_candidate_parent_commit",
    "attempt_005_candidate_parent_tree",
    "attempt_005_operator_command",
    "attempt_005_module_command",
    "attempt_005_attempted_candidate_commit",
    "attempt_005_attempted_candidate_tree",
    "attempt_005_failure_code",
    "attempt_005_cleanup_failure_codes",
    "attempt_005_run_id",
    "attempt_005_compose_project",
    "attempt_005_disposition_json",
    "attempt_005_disposition_json_sha256",
    "attempt_005_disposition_document",
    "attempt_005_disposition_document_sha256",
    "attempt_005_execution_authorized",
    "attempt_005_automatic_retry_authorized",
    "api_container_state_diagnostic_review_record",
    "api_container_state_diagnostic_review_sha256",
    "api_container_state_diagnostic_commit",
    "api_container_state_diagnostic_tree",
    "attempt_006_id",
    "attempt_006_candidate_parent_commit",
    "attempt_006_candidate_parent_tree",
    "attempt_006_operator_command",
    "attempt_006_module_command",
    "attempt_006_attempted_candidate_commit",
    "attempt_006_attempted_candidate_tree",
    "attempt_006_failure_code",
    "attempt_006_cleanup_failure_codes",
    "attempt_006_run_id",
    "attempt_006_compose_project",
    "attempt_006_disposition_json",
    "attempt_006_disposition_json_sha256",
    "attempt_006_disposition_document",
    "attempt_006_disposition_document_sha256",
    "attempt_006_execution_authorized",
    "attempt_006_automatic_retry_authorized",
    "application_startup_stage_diagnostic_review_record",
    "application_startup_stage_diagnostic_review_sha256",
    "application_startup_stage_diagnostic_commit",
    "application_startup_stage_diagnostic_tree",
    "application_startup_stage_diagnostic_path_digests",
    "attempt_007_id",
    "attempt_007_candidate_parent_commit",
    "attempt_007_candidate_parent_tree",
    "attempt_007_operator_command",
    "attempt_007_module_command",
    "attempt_007_attempted_candidate_commit",
    "attempt_007_attempted_candidate_tree",
    "attempt_007_failure_code",
    "attempt_007_cleanup_failure_codes",
    "attempt_007_run_id",
    "attempt_007_compose_project",
    "attempt_007_disposition_json",
    "attempt_007_disposition_json_sha256",
    "attempt_007_disposition_document",
    "attempt_007_disposition_document_sha256",
    "attempt_007_execution_authorized",
    "attempt_007_automatic_retry_authorized",
    "image_readability_repair_review_record",
    "image_readability_repair_review_sha256",
    "image_readability_repair_commit",
    "image_readability_repair_tree",
    "image_readability_repair_path_digests",
    "attempt_008_id",
    "attempt_008_candidate_parent_commit",
    "attempt_008_candidate_parent_tree",
    "attempt_008_operator_command",
    "attempt_008_module_command",
    "attempt_008_attempted_candidate_commit",
    "attempt_008_attempted_candidate_tree",
    "attempt_008_failure_code",
    "attempt_008_primary_failure_code",
    "attempt_008_cleanup_failure_codes",
    "attempt_008_run_id",
    "attempt_008_compose_project",
    "attempt_008_disposition_json",
    "attempt_008_disposition_json_sha256",
    "attempt_008_disposition_document",
    "attempt_008_disposition_document_sha256",
    "attempt_008_execution_authorized",
    "attempt_008_automatic_retry_authorized",
    "enrollment_output_projection_repair_review_record",
    "enrollment_output_projection_repair_review_sha256",
    "enrollment_output_projection_repair_rejected_commit",
    "enrollment_output_projection_repair_rejected_tree",
    "enrollment_output_projection_repair_commit",
    "enrollment_output_projection_repair_tree",
    "enrollment_output_projection_repair_path_digests",
    "enrollment_output_projection_contract",
    "attempt_009_id",
    "attempt_009_candidate_parent_commit",
    "attempt_009_candidate_parent_tree",
    "attempt_009_operator_command",
    "attempt_009_module_command",
    "attempt_009_kind",
    "attempt_009_run_identity_source",
    "attempt_009_preflight_fail_closed_before_live_work",
    "attempt_009_execution_authorized",
    "attempt_009_automatic_retry_authorized",
    "attempt_002_id",
    "attempt_002_candidate_parent_commit",
    "attempt_002_candidate_parent_tree",
    "attempt_002_operator_command",
    "attempt_002_module_command",
    "attempt_002_attempted_candidate_commit",
    "attempt_002_attempted_candidate_tree",
    "attempt_002_failure_code",
    "attempt_002_run_id",
    "attempt_002_compose_project",
    "attempt_002_execution_authorized",
    "attempt_002_automatic_retry_authorized",
    "execution_candidate_binding_mode",
    "execution_attempt_budget",
    "attempt_consumed",
    "retry_authorized",
    "attempt_custody",
    "persistent_cross_process_budget_consumption_claimed",
    "immediate_post_attempt_disposition_recorded",
    "prior_attempt_detection_roots",
    "profile",
    "command_contract",
    "external_preflight_requirements",
    "evidence_contract",
    "cleanup_contract",
    "authority",
}
EXPECTED_PROFILE: JsonObject = {
    "profile_id": "ithildin-fixed-hermes-node-bridge-v1",
    "canonical_profile_sha256": PROFILE_DIGEST,
    **{key: digest for key, (_, digest) in SOURCE_DIGESTS.items()},
    "hermes_oci_index_digest": (
        "sha256:6705aac1f41c5faca559858611ce696b760d858b73fa3b51be11599c73ba1ffc"
    ),
    "hermes_platform_digests": {
        "linux/amd64": ("sha256:48420b0abcf18f9f33cfa1da4c4e8bbd4ad107a0ddc52e5fb3ebb34a9fd20149"),
        "linux/arm64": ("sha256:bca5bafd0292bdf0d4b4b975780e96c0ec9e428e08941a87aacddb116663ce13"),
    },
    "provider_type": "custom",
    "provider_base_url": "http://host.docker.internal:11434/v1",
    "host_preflight_base_url": "http://127.0.0.1:11434",
    "provider_model": "gemma4:e4b",
    "container_provider_routing_runtime_unknown": True,
    "cloud_credentials_allowed": False,
}
EXPECTED_COMMAND_CONTRACT: JsonObject = {
    "dynamic_values": [
        "run_id",
        "unique_compose_project",
        "anchored_runtime_paths",
        "anchored_exact_candidate_snapshot_paths",
        "run_specific_image_references",
        "exact_inspected_image_ids",
        "exact_bound_image_identities",
        "stable_primary_and_cleanup_failure_codes",
    ],
    "fixed_actions": cast(list[JsonValue], FIXED_ACTIONS),
    "absent_image_id_probe_stdout_allowlist": ["", "\n"],
    "base_service_start_diagnostic": {
        "trigger": "base_services_start_failed",
        "compose_arguments": [
            "ps",
            "--all",
            "--format",
            "{{.Service}}\t{{.State}}\t{{.Health}}\t{{.ExitCode}}",
            "ithildin-api",
            "ithildin-ui",
        ],
        "combined_output_max_bytes": 1024,
        "raw_output_persisted": False,
        "closed_parse_or_fallback_required": True,
    },
    "api_container_state_diagnostic": {
        "trigger": "failed_up_and_api_service_exited_nonzero",
        "identity_query": [
            "compose",
            "ps",
            "--all",
            "--quiet",
            "ithildin-api",
        ],
        "inspect_scope": "one_exact_validated_bound_64_hex_container_id",
        "inspect_fields": [
            "container_id_match",
            "compose_project",
            "compose_service",
            "state_status",
            "state_running",
            "state_exit_code",
            "state_oom_killed",
            "state_dead",
            "state_error_present",
            "health_status",
        ],
        "combined_output_max_bytes_per_command": 512,
        "command_timeout_seconds": 10,
        "closed_parse_or_fallback_required": True,
        "bounded_process_teardown_required": True,
        "raw_output_persisted": False,
        "container_id_persisted": False,
        "raw_error_persisted": False,
        "logs_environment_mounts_config_or_command_persisted": False,
        "cause_claimed": False,
        "primary_failure_invariant": "base_services_start_failed",
        "cleanup_classification_invariant": True,
    },
    "application_startup_stage_diagnostic": {
        "trigger": (
            "failed_up_and_api_service_exited_nonzero_and_"
            "api_application_exit_nonzero_no_engine_error"
        ),
        "closed_stage_count": 12,
        "source": "application_emitted_canonical_owner_only_marker",
        "source_max_bytes": 256,
        "normalized_retained_fields": [
            "collection_status",
            "collection_reason_code",
            "last_emitted_stage",
        ],
        "missing_or_unsafe_stage": "unknown",
        "log_scraping_allowed": False,
        "raw_application_output_persisted": False,
        "root_cause_claimed": False,
        "success_predicted": False,
        "primary_failure_invariant": "base_services_start_failed",
        "cleanup_classification_invariant": True,
    },
    "arbitrary_command_allowed": False,
    "arbitrary_argument_allowed": False,
    "arbitrary_path_allowed": False,
    "arbitrary_provider_allowed": False,
    "arbitrary_model_allowed": False,
    "arbitrary_tool_allowed": False,
}
EXPECTED_EVIDENCE_CONTRACT: JsonObject = {
    "mission_template_id": "synthetic_read_review_v1",
    "mission_count": 1,
    "hermes_execution_attempts_maximum": 1,
    "automatic_retry_allowed": False,
    "gateway_operation_bindings_source": "mission_detail_plus_agent_run_detail_timeline",
    "gateway_mission_lifecycle_state": "runner_reported_succeeded",
    "gateway_agent_run_record_status": "active",
    "gateway_completed_timeline_event_type": "tool.execution.completed",
    "gateway_completed_timeline_event_count": 2,
    "runner_authored_operation_counts_trusted": False,
    "synthesized_agent_run_completion_allowed": False,
    "hermes_stdout_destination": "DEVNULL_AT_SUBPROCESS_CREATION",
    "hermes_stderr_destination": "DEVNULL_AT_SUBPROCESS_CREATION",
    "hermes_output_materialized": False,
    "hermes_retained_classifications": ["exit", "timeout", "interruption"],
    "container_provider_route_failure_consumes_attempt": True,
    "future_fake_tests_require_devnull_streams": True,
    "build_receipt_mode": "0600",
    "journey_receipt_mode": "0600",
    "image_artifact_inventory_field": "image_artifact_inventory_digest",
    "license_source_inventory_field": "license_source_inventory_digest",
    "future_assembler_schema_reconciliation_required": False,
    "current_assembler_usable_for_live_producer": True,
    "future_reconciled_assembler_and_checker_required": False,
    "bounded_image_artifact_inventory_required": True,
    "bounded_image_metadata_fields": [
        "reference",
        "image_id",
        "platform",
        "config_digest",
        "ordered_layer_digests",
    ],
    "bounded_license_source_inventory_required": True,
    "license_inventory_source": "private_exact_candidate_snapshot_no_follow_size_limited",
    "license_source_file_max_bytes": 1048576,
    "current_tracked_license_inventory_inputs": ["pyproject.toml", "uv.lock"],
    "current_tracked_license_family_files": [],
    "license_family_patterns": ["LICENSE*", "NOTICE*", "COPYING*"],
    "static_snapshot_enumeration_and_path_replacement_rejection_proven": True,
    "transient_malicious_same_uid_mutation_during_docker_context_read_proven_absent": (False),
    "operating_system_snapshot_immutability_claimed": False,
    "complete_sbom_claimed": False,
    "license_completeness_claimed": False,
    "compliance_claimed": False,
    "artifact_custody_claimed": False,
}
EXPECTED_CLEANUP_CONTRACT: JsonObject = {
    "node_revocation_required": True,
    "containers_absent_required": True,
    "volumes_absent_required": True,
    "network_absent_required": True,
    "persistent_profile_volume_absent_required": True,
    "run_specific_images_absent_required": True,
    "runtime_plaintext_absent_required": True,
    "cleanup_failure_requires_recovery": True,
    "cleanup_ambiguity_requires_stop": True,
    "early_failure_plaintext_cleanup_required": True,
    "monotonic_best_effort_cleanup_required": True,
    "enrollment_attempt_recorded_before_subprocess": True,
    "ambiguous_enrollment_retains_runtime_and_node_volume": True,
    "ambiguous_enrollment_revocation_claim_allowed": False,
    "confirmed_node_revocation_required_before_destructive_cleanup": True,
    "unconfirmed_revocation_retains_runtime_and_node_volume": True,
    "unconfirmed_revocation_safe_action": "stop_exact_fixed_node_only",
    "private_secret_free_recovery_identity_receipt_required": True,
    "recovery_identity_receipt_max_bytes": 4096,
    "recovery_identity_receipt_fields": [
        "schema_version",
        "receipt_kind",
        "run_id",
        "candidate_commit",
        "candidate_tree",
        "workspace_id",
        "node_id",
        "compose_project",
        "node_volume_name",
        "revocation_confirmed",
        "node_volume_retained",
        "anchored_runtime_retained",
        "reconciliation_required",
        "next_action",
        "release_allowed",
        "uat_complete",
    ],
    "recovery_identity_receipt_contains_credentials": False,
    "recovery_identity_receipt_published_as_success_evidence": False,
    "atomic_success_publication_required": True,
    "failed_receipt_quarantine_required": True,
    "publication_rollback_requires_name_removal_or_hidden_quarantine": True,
    "publication_rollback_base_directory_fsync_required": True,
    "chmod_only_publication_rollback_success_allowed": False,
    "retry_after_failure_automatic": False,
}
HISTORICAL_TRUE_AUTHORITY_FIELDS = {
    "producer_code_authorized",
    "docker_lifecycle_authorized",
    "live_hermes_execution_authorized",
    "model_provider_access_authorized",
    "o4_evidence_execution_authorized",
}
HISTORICAL_AUTHORITY: JsonObject = {
    key: key in HISTORICAL_TRUE_AUTHORITY_FIELDS for key in AUTHORITY_FIELDS
}
TRUE_AUTHORITY_FIELDS = {
    "producer_code_authorized",
    "docker_lifecycle_authorized",
    "live_hermes_execution_authorized",
    "model_provider_access_authorized",
    "o4_evidence_execution_authorized",
}
CLOSED_AUTHORITY: JsonObject = {key: False for key in AUTHORITY_FIELDS}
ATTEMPT_002_AUTHORITY: JsonObject = {
    key: key in HISTORICAL_TRUE_AUTHORITY_FIELDS for key in AUTHORITY_FIELDS
}
ATTEMPT_003_AUTHORITY: JsonObject = {key: False for key in AUTHORITY_FIELDS}
ATTEMPT_004_AUTHORITY: JsonObject = {key: False for key in AUTHORITY_FIELDS}
EXPECTED_AUTHORITY: JsonObject = {key: key in TRUE_AUTHORITY_FIELDS for key in AUTHORITY_FIELDS}


class O4ExecutionAuthorizationError(RuntimeError):
    """Raised when a live producer asks for unavailable authority."""


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    contract = _read_contract(repo_root / CONTRACT, failures)
    document = _read_text(repo_root / DOCUMENT, failures)
    producer_contract = _read_text(repo_root / PRODUCER_CONTRACT, failures)
    disposition = _read_contract(repo_root / DISPOSITION_JSON, failures)
    disposition_document = _read_text(repo_root / DISPOSITION_DOCUMENT, failures)
    attempt_001_disposition = _read_contract(
        repo_root / ATTEMPT_001_DISPOSITION_JSON,
        failures,
    )
    attempt_001_disposition_document = _read_text(
        repo_root / ATTEMPT_001_DISPOSITION_DOCUMENT,
        failures,
    )
    entrypoint_repair_review = _read_text(
        repo_root / ENTRYPOINT_REPAIR_REVIEW,
        failures,
    )
    attempt_002_disposition = _read_contract(
        repo_root / ATTEMPT_002_DISPOSITION_JSON,
        failures,
    )
    attempt_002_disposition_document = _read_text(
        repo_root / ATTEMPT_002_DISPOSITION_DOCUMENT,
        failures,
    )
    attempt_002_closure = _read_contract(
        repo_root / ATTEMPT_002_CLOSURE_JSON,
        failures,
    )
    attempt_002_closure_document = _read_text(
        repo_root / ATTEMPT_002_CLOSURE_DOCUMENT,
        failures,
    )
    compose_repair_review = _read_text(
        repo_root / COMPOSE_REPAIR_REVIEW,
        failures,
    )
    attempt_003_disposition = _read_contract(
        repo_root / ATTEMPT_003_DISPOSITION_JSON,
        failures,
    )
    attempt_003_disposition_document = _read_text(
        repo_root / ATTEMPT_003_DISPOSITION_DOCUMENT,
        failures,
    )
    attempt_003_closure = _read_contract(
        repo_root / ATTEMPT_003_CLOSURE_JSON,
        failures,
    )
    attempt_003_closure_document = _read_text(
        repo_root / ATTEMPT_003_CLOSURE_DOCUMENT,
        failures,
    )
    image_recovery_authorization = _read_contract(
        repo_root / IMAGE_RECOVERY_AUTHORIZATION,
        failures,
    )
    image_recovery_authorization_document = _read_text(
        repo_root / IMAGE_RECOVERY_AUTHORIZATION_DOCUMENT,
        failures,
    )
    image_recovery_closure = _read_contract(
        repo_root / IMAGE_RECOVERY_CLOSURE,
        failures,
    )
    image_recovery_closure_document = _read_text(
        repo_root / IMAGE_RECOVERY_CLOSURE_DOCUMENT,
        failures,
    )
    runtime_native_repair_review = _read_text(
        repo_root / RUNTIME_NATIVE_REPAIR_REVIEW,
        failures,
    )
    attempt_004_disposition = _read_contract(
        repo_root / ATTEMPT_004_DISPOSITION_JSON,
        failures,
    )
    attempt_004_disposition_document = _read_text(
        repo_root / ATTEMPT_004_DISPOSITION_DOCUMENT,
        failures,
    )
    diagnostic_repair_review = _read_text(
        repo_root / DIAGNOSTIC_REPAIR_REVIEW,
        failures,
    )
    attempt_005_disposition = _read_contract(
        repo_root / ATTEMPT_005_DISPOSITION_JSON,
        failures,
    )
    attempt_005_disposition_document = _read_text(
        repo_root / ATTEMPT_005_DISPOSITION_DOCUMENT,
        failures,
    )
    api_container_state_diagnostic_review = _read_text(
        repo_root / API_CONTAINER_STATE_DIAGNOSTIC_REVIEW,
        failures,
    )
    attempt_006_disposition = _read_contract(
        repo_root / ATTEMPT_006_DISPOSITION_JSON,
        failures,
    )
    attempt_006_disposition_document = _read_text(
        repo_root / ATTEMPT_006_DISPOSITION_DOCUMENT,
        failures,
    )
    application_startup_stage_diagnostic_review = _read_text(
        repo_root / APPLICATION_STARTUP_STAGE_DIAGNOSTIC_REVIEW,
        failures,
    )
    attempt_007_disposition = _read_contract(
        repo_root / ATTEMPT_007_DISPOSITION_JSON,
        failures,
    )
    attempt_007_disposition_document = _read_text(
        repo_root / ATTEMPT_007_DISPOSITION_DOCUMENT,
        failures,
    )
    image_readability_repair_review = _read_text(
        repo_root / IMAGE_READABILITY_REPAIR_REVIEW,
        failures,
    )
    attempt_008_disposition = _read_contract(
        repo_root / ATTEMPT_008_DISPOSITION_JSON,
        failures,
    )
    attempt_008_disposition_document = _read_text(
        repo_root / ATTEMPT_008_DISPOSITION_DOCUMENT,
        failures,
    )
    enrollment_output_projection_repair_review = _read_text(
        repo_root / ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REVIEW,
        failures,
    )
    _validate_contract(contract, failures)
    _validate_document(document, failures)
    _validate_producer_contract(producer_contract, contract, failures)
    _validate_disposition(disposition, disposition_document, failures)
    _validate_attempt_001_disposition(
        attempt_001_disposition,
        attempt_001_disposition_document,
        failures,
    )
    _validate_entrypoint_repair_review(entrypoint_repair_review, failures)
    _validate_attempt_002_disposition(
        attempt_002_disposition,
        attempt_002_disposition_document,
        failures,
    )
    _validate_attempt_002_closure(
        attempt_002_closure,
        attempt_002_closure_document,
        failures,
    )
    _validate_compose_repair_review(compose_repair_review, failures)
    _validate_attempt_003_disposition(
        attempt_003_disposition,
        attempt_003_disposition_document,
        failures,
    )
    _validate_attempt_003_closure(
        attempt_003_closure,
        attempt_003_closure_document,
        failures,
    )
    _validate_image_recovery_history(
        image_recovery_authorization,
        image_recovery_authorization_document,
        image_recovery_closure,
        image_recovery_closure_document,
        failures,
    )
    _validate_runtime_native_repair_review(
        runtime_native_repair_review,
        failures,
    )
    _validate_attempt_004_disposition(
        attempt_004_disposition,
        attempt_004_disposition_document,
        failures,
    )
    _validate_diagnostic_repair_review(diagnostic_repair_review, failures)
    _validate_attempt_005_disposition(
        attempt_005_disposition,
        attempt_005_disposition_document,
        failures,
    )
    _validate_api_container_state_diagnostic_review(
        api_container_state_diagnostic_review,
        failures,
    )
    _validate_attempt_006_disposition(
        attempt_006_disposition,
        attempt_006_disposition_document,
        failures,
    )
    _validate_application_startup_stage_diagnostic_review(
        application_startup_stage_diagnostic_review,
        failures,
    )
    _validate_attempt_007_disposition(
        attempt_007_disposition,
        attempt_007_disposition_document,
        failures,
    )
    _validate_image_readability_repair_review(
        image_readability_repair_review,
        failures,
    )
    _validate_attempt_008_disposition(
        attempt_008_disposition,
        attempt_008_disposition_document,
        failures,
    )
    _validate_enrollment_output_projection_repair_review(
        enrollment_output_projection_repair_review,
        failures,
    )
    _validate_retained_attempt_evidence(repo_root, failures)
    _validate_evidence_ignore_patterns(repo_root, failures)
    _validate_bound_documents(repo_root, failures)
    _validate_git_bindings(repo_root, failures)
    _validate_attempted_candidate_binding(repo_root, failures)
    _validate_attempt_002_candidate_binding(repo_root, failures)
    _validate_attempt_003_candidate_binding(repo_root, failures)
    _validate_source_bindings(repo_root, contract, failures)
    _validate_current_license_discovery(repo_root, failures)
    _validate_wiring(repo_root, failures)
    execution_checkout = _validate_execution_checkout(
        repo_root,
        failures,
        candidate_parent_commit=ENROLLMENT_OUTPUT_PROJECTION_REPAIR_COMMIT,
        candidate_parent_tree=ENROLLMENT_OUTPUT_PROJECTION_REPAIR_TREE,
        reviewed_commit=ENROLLMENT_OUTPUT_PROJECTION_REPAIR_COMMIT,
        control_paths=ATTEMPT_009_CONTROL_PATH_ALLOWLIST,
        repair_paths=ENROLLMENT_OUTPUT_PROJECTION_REPAIR_PATHS,
    )
    checkout_commit = execution_checkout[0] if execution_checkout is not None else None
    checkout_tree = execution_checkout[1] if execution_checkout is not None else None
    valid = not failures
    return {
        "schema_version": "1",
        "valid": valid,
        "failures": failures,
        "record_status": contract.get("record_status"),
        "reviewed_implementation_commit": contract.get("reviewed_implementation_commit"),
        "code_authorization_commit": contract.get("code_authorization_commit"),
        "attempt_id": contract.get("attempt_009_id"),
        "attempted_candidate_commit": checkout_commit,
        "attempted_candidate_tree": checkout_tree,
        "attempt_002_attempted_candidate_commit": contract.get(
            "attempt_002_attempted_candidate_commit"
        ),
        "attempt_002_attempted_candidate_tree": contract.get(
            "attempt_002_attempted_candidate_tree"
        ),
        "attempt_001_history": {
            "attempt_id": contract.get("attempt_001_id"),
            "attempted_candidate_commit": contract.get("attempt_001_attempted_candidate_commit"),
            "attempted_candidate_tree": contract.get("attempt_001_attempted_candidate_tree"),
            "attempt_consumed": True,
        },
        "attempt_002_history": {
            "attempt_id": contract.get("attempt_002_id"),
            "attempted_candidate_commit": contract.get("attempt_002_attempted_candidate_commit"),
            "attempted_candidate_tree": contract.get("attempt_002_attempted_candidate_tree"),
            "attempt_consumed": True,
        },
        "attempt_003_history": {
            "attempt_id": contract.get("attempt_003_id"),
            "attempted_candidate_commit": contract.get("attempt_003_attempted_candidate_commit"),
            "attempted_candidate_tree": contract.get("attempt_003_attempted_candidate_tree"),
            "attempt_consumed": True,
        },
        "attempt_004_history": {
            "attempt_id": contract.get("attempt_004_id"),
            "attempted_candidate_commit": contract.get("attempt_004_attempted_candidate_commit"),
            "attempted_candidate_tree": contract.get("attempt_004_attempted_candidate_tree"),
            "attempt_consumed": True,
        },
        "attempt_005_history": {
            "attempt_id": contract.get("attempt_005_id"),
            "attempted_candidate_commit": contract.get("attempt_005_attempted_candidate_commit"),
            "attempted_candidate_tree": contract.get("attempt_005_attempted_candidate_tree"),
            "attempt_consumed": True,
        },
        "attempt_001_consumed": True,
        "attempt_002_consumed": True,
        "attempt_003_consumed": True,
        "attempt_004_consumed": True,
        "attempt_005_consumed": True,
        "attempt_006_consumed": True,
        "attempt_007_consumed": True,
        "attempt_008_consumed": True,
        "attempt_009_consumed": contract.get("attempt_consumed"),
        "attempt_consumed": contract.get("attempt_consumed"),
        "retry_authorized": contract.get("retry_authorized"),
        "execution_checkout_commit": checkout_commit,
        "execution_checkout_tree": checkout_tree,
        "execution_attempt_budget": 1 if valid else 0,
        "live_execution_authorized": valid,
        "docker_lifecycle_authorized": valid,
        "provider_access_authorized": valid,
        "o4_evidence_execution_authorized": valid,
        "new_governed_tool": False,
        "release_allowed": False,
        "uat_complete": False,
    }


def assert_live_execution_authorized(
    repo_root: Path,
    *,
    candidate_commit: str,
    candidate_tree: str,
) -> None:
    report = build_report(repo_root)
    if (
        not report["valid"]
        or report["live_execution_authorized"] is not True
        or report["execution_attempt_budget"] != 1
        or report["execution_checkout_commit"] != candidate_commit
        or report["execution_checkout_tree"] != candidate_tree
    ):
        raise O4ExecutionAuthorizationError("o4_live_execution_not_authorized")


def _validate_contract(contract: JsonObject, failures: list[str]) -> None:
    if set(contract) != TOP_LEVEL_FIELDS:
        failures.append("O4 execution authorization fields are not closed")
    expected = {
        "schema_version": "1",
        "record_type": "local_v1_lv1_003_o4_execution_authorization",
        "record_status": "ATTEMPT_009_EXACT_CHILD_ONE_SHOT_EXECUTION_AUTHORIZED",
        "ticket_id": "LV1-003",
        "outcome_id": "O4",
        "producer_contract_path": PRODUCER_CONTRACT.as_posix(),
        "producer_contract_sha256": PRODUCER_CONTRACT_DIGEST,
        "candidate_parent_commit": CANDIDATE_PARENT_COMMIT,
        "candidate_parent_tree": CANDIDATE_PARENT_TREE,
        "historical_post_review_candidate_parent_commit": (HISTORICAL_CANDIDATE_PARENT_COMMIT),
        "historical_post_review_candidate_parent_tree": (HISTORICAL_CANDIDATE_PARENT_TREE),
        "reviewed_implementation_commit": REVIEWED_IMPLEMENTATION_COMMIT,
        "reviewed_implementation_tree": REVIEWED_IMPLEMENTATION_TREE,
        "producer_exact_review_record": PRODUCER_EXACT_REVIEW.as_posix(),
        "producer_exact_review_sha256": PRODUCER_EXACT_REVIEW_DIGEST,
        "code_authorization_origin_commit": CODE_AUTHORIZATION_ORIGIN_COMMIT,
        "code_authorization_origin_tree": CODE_AUTHORIZATION_ORIGIN_TREE,
        "code_authorization_commit": CODE_AUTHORIZATION_COMMIT,
        "code_authorization_tree": CODE_AUTHORIZATION_TREE,
        "code_authorization_origin_record_sha256": (CODE_AUTHORIZATION_ORIGIN_RECORD_DIGEST),
        "code_authorization_record_sha256": CODE_AUTHORIZATION_RECORD_DIGEST,
        "post_review_disposition_json": DISPOSITION_JSON.as_posix(),
        "post_review_disposition_json_sha256": DISPOSITION_JSON_DIGEST,
        "post_review_disposition_document": DISPOSITION_DOCUMENT.as_posix(),
        "post_review_disposition_document_sha256": DISPOSITION_DOCUMENT_DIGEST,
        "attempt_001_disposition_json": ATTEMPT_001_DISPOSITION_JSON.as_posix(),
        "attempt_001_disposition_json_sha256": ATTEMPT_001_DISPOSITION_JSON_DIGEST,
        "attempt_001_disposition_document": ATTEMPT_001_DISPOSITION_DOCUMENT.as_posix(),
        "attempt_001_disposition_document_sha256": ATTEMPT_001_DISPOSITION_DOCUMENT_DIGEST,
        "attempt_001_id": ATTEMPT_001_ID,
        "attempt_001_attempted_candidate_commit": ATTEMPT_001_CANDIDATE_COMMIT,
        "attempt_001_attempted_candidate_tree": ATTEMPT_001_CANDIDATE_TREE,
        "attempt_001_attempted_authorization_contract_sha256": (
            ATTEMPT_001_AUTHORIZATION_CONTRACT_DIGEST
        ),
        "attempt_001_invocation": {
            "command": ATTEMPT_001_COMMAND,
            "exit_code": 1,
            "classification": "PRE_GATE_MODULE_IMPORT_FAILURE",
            "exception_type": "ModuleNotFoundError",
            "exception_message": "No module named 'scripts'",
            "failure_location": "scripts/local_v1_lv1_003_o4_producer.py:36",
            "gate_authorization_entered": False,
            "producer_runtime_entered": False,
        },
        "attempt_001_root_absence": {
            "observation_method": "read_only_path_absence_check_after_failed_invocation",
            "absent_roots": cast(list[JsonValue], PRIOR_ATTEMPT_ROOTS),
        },
        "producer_entrypoint_repair": {
            "status": "IMPLEMENTED_PENDING_EXACT_REVIEW_NO_RETRY_AUTHORITY",
            "base_closure_commit": ENTRYPOINT_REPAIR_BASE_COMMIT,
            "live_make_target": PRODUCER_RUN_TARGET,
            "module_invocation": PRODUCER_MODULE_INVOCATION,
            "failed_file_path_invocation": FAILED_FILE_PATH_INVOCATION,
            "failed_file_path_invocation_authorized": False,
            "module_import_executes_main": False,
            "independent_exact_review_required": True,
            "separate_new_attempt_disposition_required": True,
        },
        "entrypoint_repair_review_record": ENTRYPOINT_REPAIR_REVIEW.as_posix(),
        "entrypoint_repair_review_sha256": ENTRYPOINT_REPAIR_REVIEW_DIGEST,
        "attempt_002_disposition_json": ATTEMPT_002_DISPOSITION_JSON.as_posix(),
        "attempt_002_disposition_json_sha256": (ATTEMPT_002_DISPOSITION_JSON_DIGEST),
        "attempt_002_disposition_document": (ATTEMPT_002_DISPOSITION_DOCUMENT.as_posix()),
        "attempt_002_disposition_document_sha256": (ATTEMPT_002_DISPOSITION_DOCUMENT_DIGEST),
        "attempt_002_closure_json": ATTEMPT_002_CLOSURE_JSON.as_posix(),
        "attempt_002_closure_json_sha256": ATTEMPT_002_CLOSURE_JSON_DIGEST,
        "attempt_002_closure_document": ATTEMPT_002_CLOSURE_DOCUMENT.as_posix(),
        "attempt_002_closure_document_sha256": (ATTEMPT_002_CLOSURE_DOCUMENT_DIGEST),
        "compose_repair_review_record": COMPOSE_REPAIR_REVIEW.as_posix(),
        "compose_repair_review_sha256": COMPOSE_REPAIR_REVIEW_DIGEST,
        "attempt_003_disposition_json": ATTEMPT_003_DISPOSITION_JSON.as_posix(),
        "attempt_003_disposition_json_sha256": (ATTEMPT_003_DISPOSITION_JSON_DIGEST),
        "attempt_003_disposition_document": (ATTEMPT_003_DISPOSITION_DOCUMENT.as_posix()),
        "attempt_003_disposition_document_sha256": (ATTEMPT_003_DISPOSITION_DOCUMENT_DIGEST),
        "attempt_003_closure_json": ATTEMPT_003_CLOSURE_JSON.as_posix(),
        "attempt_003_closure_json_sha256": ATTEMPT_003_CLOSURE_JSON_DIGEST,
        "attempt_003_closure_document": ATTEMPT_003_CLOSURE_DOCUMENT.as_posix(),
        "attempt_003_closure_document_sha256": (ATTEMPT_003_CLOSURE_DOCUMENT_DIGEST),
        "attempt_003_id": ATTEMPT_003_ID,
        "attempt_003_candidate_parent_commit": COMPOSE_REPAIR_COMMIT,
        "attempt_003_candidate_parent_tree": COMPOSE_REPAIR_TREE,
        "attempt_003_operator_command": ATTEMPT_002_OPERATOR_COMMAND,
        "attempt_003_module_command": PRODUCER_MODULE_INVOCATION,
        "attempt_003_attempted_candidate_commit": ATTEMPT_003_CANDIDATE_COMMIT,
        "attempt_003_attempted_candidate_tree": ATTEMPT_003_CANDIDATE_TREE,
        "attempt_003_failure_code": "recovery_required",
        "attempt_003_run_id": ATTEMPT_003_RUN_ID,
        "attempt_003_compose_project": ATTEMPT_003_PROJECT,
        "attempt_003_execution_authorized": False,
        "attempt_003_automatic_retry_authorized": False,
        "attempt_003_recovery_authorized": False,
        "image_recovery_authorization_json": IMAGE_RECOVERY_AUTHORIZATION.as_posix(),
        "image_recovery_authorization_json_sha256": (IMAGE_RECOVERY_AUTHORIZATION_DIGEST),
        "image_recovery_authorization_document": (IMAGE_RECOVERY_AUTHORIZATION_DOCUMENT.as_posix()),
        "image_recovery_authorization_document_sha256": (
            IMAGE_RECOVERY_AUTHORIZATION_DOCUMENT_DIGEST
        ),
        "image_recovery_closure_json": IMAGE_RECOVERY_CLOSURE.as_posix(),
        "image_recovery_closure_json_sha256": IMAGE_RECOVERY_CLOSURE_DIGEST,
        "image_recovery_closure_document": (IMAGE_RECOVERY_CLOSURE_DOCUMENT.as_posix()),
        "image_recovery_closure_document_sha256": (IMAGE_RECOVERY_CLOSURE_DOCUMENT_DIGEST),
        "image_recovery_history": {
            "recovery_id": IMAGE_RECOVERY_ID,
            "recovery_candidate_commit": IMAGE_RECOVERY_CANDIDATE_COMMIT,
            "recovery_candidate_tree": IMAGE_RECOVERY_CANDIDATE_TREE,
            "closure_commit": IMAGE_RECOVERY_CLOSURE_COMMIT,
            "closure_tree": IMAGE_RECOVERY_CLOSURE_TREE,
            "status": "RECOVERY_COMPLETED_EXACT_IMAGE_REMOVAL_CLOSED",
            "consumed": True,
            "retry_authorized": False,
            "receipt_retained": True,
            "receipt_removal_authorized": False,
        },
        "runtime_native_repair_review_record": (RUNTIME_NATIVE_REPAIR_REVIEW.as_posix()),
        "runtime_native_repair_review_sha256": (RUNTIME_NATIVE_REPAIR_REVIEW_DIGEST),
        "runtime_native_repair_commit": RUNTIME_NATIVE_REPAIR_COMMIT,
        "runtime_native_repair_tree": RUNTIME_NATIVE_REPAIR_TREE,
        "attempt_004_id": ATTEMPT_004_ID,
        "attempt_004_candidate_parent_commit": RUNTIME_NATIVE_REPAIR_COMMIT,
        "attempt_004_candidate_parent_tree": RUNTIME_NATIVE_REPAIR_TREE,
        "attempt_004_operator_command": ATTEMPT_002_OPERATOR_COMMAND,
        "attempt_004_module_command": PRODUCER_MODULE_INVOCATION,
        "attempt_004_attempted_candidate_commit": ATTEMPT_004_CANDIDATE_COMMIT,
        "attempt_004_attempted_candidate_tree": ATTEMPT_004_CANDIDATE_TREE,
        "attempt_004_failure_code": "recovery_required",
        "attempt_004_primary_failure_code": "base_services_start_failed",
        "attempt_004_cleanup_failure_codes": ["owned_image_id_absence_probe_failed"],
        "attempt_004_run_id": ATTEMPT_004_RUN_ID,
        "attempt_004_compose_project": ATTEMPT_004_PROJECT,
        "attempt_004_disposition_json": ATTEMPT_004_DISPOSITION_JSON.as_posix(),
        "attempt_004_disposition_json_sha256": ATTEMPT_004_DISPOSITION_JSON_DIGEST,
        "attempt_004_disposition_document": ATTEMPT_004_DISPOSITION_DOCUMENT.as_posix(),
        "attempt_004_disposition_document_sha256": (ATTEMPT_004_DISPOSITION_DOCUMENT_DIGEST),
        "attempt_004_closure_commit": ATTEMPT_004_CLOSURE_COMMIT,
        "attempt_004_closure_tree": ATTEMPT_004_CLOSURE_TREE,
        "attempt_004_execution_authorized": False,
        "attempt_004_automatic_retry_authorized": False,
        "diagnostic_repair_review_record": DIAGNOSTIC_REPAIR_REVIEW.as_posix(),
        "diagnostic_repair_review_sha256": DIAGNOSTIC_REPAIR_REVIEW_DIGEST,
        "diagnostic_repair_commit": DIAGNOSTIC_REPAIR_COMMIT,
        "diagnostic_repair_tree": DIAGNOSTIC_REPAIR_TREE,
        "attempt_005_id": ATTEMPT_005_ID,
        "attempt_005_candidate_parent_commit": DIAGNOSTIC_REPAIR_COMMIT,
        "attempt_005_candidate_parent_tree": DIAGNOSTIC_REPAIR_TREE,
        "attempt_005_operator_command": ATTEMPT_002_OPERATOR_COMMAND,
        "attempt_005_module_command": PRODUCER_MODULE_INVOCATION,
        "attempt_005_attempted_candidate_commit": ATTEMPT_005_CANDIDATE_COMMIT,
        "attempt_005_attempted_candidate_tree": ATTEMPT_005_CANDIDATE_TREE,
        "attempt_005_failure_code": "base_services_start_failed",
        "attempt_005_cleanup_failure_codes": [],
        "attempt_005_run_id": ATTEMPT_005_RUN_ID,
        "attempt_005_compose_project": ATTEMPT_005_PROJECT,
        "attempt_005_disposition_json": ATTEMPT_005_DISPOSITION_JSON.as_posix(),
        "attempt_005_disposition_json_sha256": ATTEMPT_005_DISPOSITION_JSON_DIGEST,
        "attempt_005_disposition_document": ATTEMPT_005_DISPOSITION_DOCUMENT.as_posix(),
        "attempt_005_disposition_document_sha256": ATTEMPT_005_DISPOSITION_DOCUMENT_DIGEST,
        "attempt_005_execution_authorized": False,
        "attempt_005_automatic_retry_authorized": False,
        "api_container_state_diagnostic_review_record": (
            API_CONTAINER_STATE_DIAGNOSTIC_REVIEW.as_posix()
        ),
        "api_container_state_diagnostic_review_sha256": (
            API_CONTAINER_STATE_DIAGNOSTIC_REVIEW_DIGEST
        ),
        "api_container_state_diagnostic_commit": API_CONTAINER_STATE_DIAGNOSTIC_COMMIT,
        "api_container_state_diagnostic_tree": API_CONTAINER_STATE_DIAGNOSTIC_TREE,
        "attempt_006_id": ATTEMPT_006_ID,
        "attempt_006_candidate_parent_commit": API_CONTAINER_STATE_DIAGNOSTIC_COMMIT,
        "attempt_006_candidate_parent_tree": API_CONTAINER_STATE_DIAGNOSTIC_TREE,
        "attempt_006_operator_command": ATTEMPT_002_OPERATOR_COMMAND,
        "attempt_006_module_command": PRODUCER_MODULE_INVOCATION,
        "attempt_006_attempted_candidate_commit": ATTEMPT_006_CANDIDATE_COMMIT,
        "attempt_006_attempted_candidate_tree": ATTEMPT_006_CANDIDATE_TREE,
        "attempt_006_failure_code": "base_services_start_failed",
        "attempt_006_cleanup_failure_codes": [],
        "attempt_006_run_id": ATTEMPT_006_RUN_ID,
        "attempt_006_compose_project": ATTEMPT_006_PROJECT,
        "attempt_006_disposition_json": ATTEMPT_006_DISPOSITION_JSON.as_posix(),
        "attempt_006_disposition_json_sha256": ATTEMPT_006_DISPOSITION_JSON_DIGEST,
        "attempt_006_disposition_document": ATTEMPT_006_DISPOSITION_DOCUMENT.as_posix(),
        "attempt_006_disposition_document_sha256": (ATTEMPT_006_DISPOSITION_DOCUMENT_DIGEST),
        "attempt_006_execution_authorized": False,
        "attempt_006_automatic_retry_authorized": False,
        "application_startup_stage_diagnostic_review_record": (
            APPLICATION_STARTUP_STAGE_DIAGNOSTIC_REVIEW.as_posix()
        ),
        "application_startup_stage_diagnostic_review_sha256": (
            APPLICATION_STARTUP_STAGE_DIAGNOSTIC_REVIEW_DIGEST
        ),
        "application_startup_stage_diagnostic_commit": (
            APPLICATION_STARTUP_STAGE_DIAGNOSTIC_COMMIT
        ),
        "application_startup_stage_diagnostic_tree": (APPLICATION_STARTUP_STAGE_DIAGNOSTIC_TREE),
        "application_startup_stage_diagnostic_path_digests": (
            APPLICATION_STARTUP_STAGE_PATH_DIGESTS
        ),
        "attempt_007_id": ATTEMPT_007_ID,
        "attempt_007_candidate_parent_commit": APPLICATION_STARTUP_STAGE_DIAGNOSTIC_COMMIT,
        "attempt_007_candidate_parent_tree": APPLICATION_STARTUP_STAGE_DIAGNOSTIC_TREE,
        "attempt_007_operator_command": ATTEMPT_002_OPERATOR_COMMAND,
        "attempt_007_module_command": PRODUCER_MODULE_INVOCATION,
        "attempt_007_attempted_candidate_commit": ATTEMPT_007_CANDIDATE_COMMIT,
        "attempt_007_attempted_candidate_tree": ATTEMPT_007_CANDIDATE_TREE,
        "attempt_007_failure_code": "base_services_start_failed",
        "attempt_007_cleanup_failure_codes": [],
        "attempt_007_run_id": ATTEMPT_007_RUN_ID,
        "attempt_007_compose_project": ATTEMPT_007_PROJECT,
        "attempt_007_disposition_json": ATTEMPT_007_DISPOSITION_JSON.as_posix(),
        "attempt_007_disposition_json_sha256": ATTEMPT_007_DISPOSITION_JSON_DIGEST,
        "attempt_007_disposition_document": ATTEMPT_007_DISPOSITION_DOCUMENT.as_posix(),
        "attempt_007_disposition_document_sha256": (ATTEMPT_007_DISPOSITION_DOCUMENT_DIGEST),
        "attempt_007_execution_authorized": False,
        "attempt_007_automatic_retry_authorized": False,
        "image_readability_repair_review_record": (IMAGE_READABILITY_REPAIR_REVIEW.as_posix()),
        "image_readability_repair_review_sha256": (IMAGE_READABILITY_REPAIR_REVIEW_DIGEST),
        "image_readability_repair_commit": IMAGE_READABILITY_REPAIR_COMMIT,
        "image_readability_repair_tree": IMAGE_READABILITY_REPAIR_TREE,
        "image_readability_repair_path_digests": IMAGE_READABILITY_REPAIR_PATH_DIGESTS,
        "attempt_008_id": ATTEMPT_008_ID,
        "attempt_008_candidate_parent_commit": IMAGE_READABILITY_REPAIR_COMMIT,
        "attempt_008_candidate_parent_tree": IMAGE_READABILITY_REPAIR_TREE,
        "attempt_008_operator_command": ATTEMPT_002_OPERATOR_COMMAND,
        "attempt_008_module_command": PRODUCER_MODULE_INVOCATION,
        "attempt_008_attempted_candidate_commit": ATTEMPT_008_CANDIDATE_COMMIT,
        "attempt_008_attempted_candidate_tree": ATTEMPT_008_CANDIDATE_TREE,
        "attempt_008_failure_code": "recovery_required",
        "attempt_008_primary_failure_code": "subprocess_output_rejected",
        "attempt_008_cleanup_failure_codes": ["enrollment_outcome_ambiguous"],
        "attempt_008_run_id": ATTEMPT_008_RUN_ID,
        "attempt_008_compose_project": ATTEMPT_008_PROJECT,
        "attempt_008_disposition_json": ATTEMPT_008_DISPOSITION_JSON.as_posix(),
        "attempt_008_disposition_json_sha256": ATTEMPT_008_DISPOSITION_JSON_DIGEST,
        "attempt_008_disposition_document": ATTEMPT_008_DISPOSITION_DOCUMENT.as_posix(),
        "attempt_008_disposition_document_sha256": (ATTEMPT_008_DISPOSITION_DOCUMENT_DIGEST),
        "attempt_008_execution_authorized": False,
        "attempt_008_automatic_retry_authorized": False,
        "enrollment_output_projection_repair_review_record": (
            ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REVIEW.as_posix()
        ),
        "enrollment_output_projection_repair_review_sha256": (
            ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REVIEW_DIGEST
        ),
        "enrollment_output_projection_repair_rejected_commit": (
            ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REJECTED_COMMIT
        ),
        "enrollment_output_projection_repair_rejected_tree": (
            ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REJECTED_TREE
        ),
        "enrollment_output_projection_repair_commit": (ENROLLMENT_OUTPUT_PROJECTION_REPAIR_COMMIT),
        "enrollment_output_projection_repair_tree": ENROLLMENT_OUTPUT_PROJECTION_REPAIR_TREE,
        "enrollment_output_projection_repair_path_digests": (
            ENROLLMENT_OUTPUT_PROJECTION_REPAIR_PATH_DIGESTS
        ),
        "enrollment_output_projection_contract": {
            "field_names": ["node_id", "principal_id", "workspace_id"],
            "field_types": {
                "node_id": "string",
                "principal_id": "string",
                "workspace_id": "string",
            },
            "principal_id_derivation": "agent:node.{node_id}",
            "canonical_json_terminated_by_one_lf": True,
            "extra_fields_allowed": False,
        },
        "attempt_009_id": ATTEMPT_009_ID,
        "attempt_009_candidate_parent_commit": ENROLLMENT_OUTPUT_PROJECTION_REPAIR_COMMIT,
        "attempt_009_candidate_parent_tree": ENROLLMENT_OUTPUT_PROJECTION_REPAIR_TREE,
        "attempt_009_operator_command": ATTEMPT_002_OPERATOR_COMMAND,
        "attempt_009_module_command": PRODUCER_MODULE_INVOCATION,
        "attempt_009_kind": (
            "new_separately_authorized_isolated_attempt_not_retry_cleanup_or_reconciliation"
        ),
        "attempt_009_run_identity_source": (
            "producer_generated_fresh_run_project_suffix_runtime_receipt_and_evidence_paths"
        ),
        "attempt_009_preflight_fail_closed_before_live_work": True,
        "attempt_009_execution_authorized": True,
        "attempt_009_automatic_retry_authorized": False,
        "attempt_002_id": ATTEMPT_002_ID,
        "attempt_002_candidate_parent_commit": ENTRYPOINT_REPAIR_COMMIT,
        "attempt_002_candidate_parent_tree": ENTRYPOINT_REPAIR_TREE,
        "attempt_002_operator_command": ATTEMPT_002_OPERATOR_COMMAND,
        "attempt_002_module_command": PRODUCER_MODULE_INVOCATION,
        "attempt_002_attempted_candidate_commit": ATTEMPT_002_CANDIDATE_COMMIT,
        "attempt_002_attempted_candidate_tree": ATTEMPT_002_CANDIDATE_TREE,
        "attempt_002_failure_code": "fixed_compose_invalid",
        "attempt_002_run_id": ATTEMPT_002_RUN_ID,
        "attempt_002_compose_project": ATTEMPT_002_PROJECT,
        "attempt_002_execution_authorized": False,
        "attempt_002_automatic_retry_authorized": False,
        "execution_candidate_binding_mode": "dynamic_current_head_after_all_checks",
        "execution_attempt_budget": 1,
        "attempt_consumed": False,
        "retry_authorized": False,
        "attempt_custody": "central_manager_supervised_local_invocation",
        "persistent_cross_process_budget_consumption_claimed": False,
        "immediate_post_attempt_disposition_recorded": False,
        "prior_attempt_detection_roots": PRIOR_ATTEMPT_ROOTS,
        "external_preflight_requirements": EXTERNAL_PREFLIGHT,
    }
    for key, value in expected.items():
        if not _exact_json_equal(contract.get(key), value):
            failures.append(f"O4 execution authorization {key} is not exact")
    if not _exact_json_equal(contract.get("profile"), EXPECTED_PROFILE):
        failures.append("O4 execution profile binding is not exact")
    if not _exact_json_equal(
        contract.get("command_contract"),
        EXPECTED_COMMAND_CONTRACT,
    ):
        failures.append("O4 execution command contract is invalid")
    if not _exact_json_equal(
        contract.get("evidence_contract"),
        EXPECTED_EVIDENCE_CONTRACT,
    ):
        failures.append("O4 execution evidence contract is invalid")
    if not _exact_json_equal(
        contract.get("cleanup_contract"),
        EXPECTED_CLEANUP_CONTRACT,
    ):
        failures.append("O4 execution cleanup contract is invalid")
    if not _exact_json_equal(contract.get("authority"), EXPECTED_AUTHORITY):
        failures.append("O4 execution authority is not exact for Attempt 009")


def _validate_document(document: str, failures: list[str]) -> None:
    normalized = " ".join(document.split())
    for phrase in (
        "Status: `ATTEMPT_009_EXACT_CHILD_ONE_SHOT_EXECUTION_AUTHORIZED`",
        REVIEWED_IMPLEMENTATION_COMMIT,
        CANDIDATE_PARENT_COMMIT,
        HISTORICAL_CANDIDATE_PARENT_COMMIT,
        CODE_AUTHORIZATION_COMMIT,
        "all inherited Attempt 001 lineage with explicit `attempt_001_*` keys",
        "Those fields are historical only",
        "public current-attempt fields bind the dynamic Attempt 009 child",
        ATTEMPT_001_CANDIDATE_COMMIT,
        ATTEMPT_001_CANDIDATE_TREE,
        ATTEMPT_001_COMMAND,
        "exited `1` before gate authorization or producer runtime entry",
        "`ModuleNotFoundError: No module named 'scripts'`",
        "receipt, runtime, and constrained-journey report roots absent",
        "performed no runtime creation, Docker, Ollama or provider, API, Node, Hermes, "
        "credential, network journey, or evidence action",
        "make local-v1-lv1-003-o4-producer-run",
        "`uv run python -m scripts.local_v1_lv1_003_o4_producer`",
        "failed command `uv run python scripts/local_v1_lv1_003_o4_producer.py` is not "
        "an authorized future invocation",
        "Importing that module does not execute its `main` function",
        ENTRYPOINT_REPAIR_COMMIT,
        ENTRYPOINT_REPAIR_TREE,
        "received independent exact review with zero Critical, High, Medium, or Low findings",
        ATTEMPT_002_DISPOSITION_JSON.as_posix(),
        "outside release, milestone, static, and authorization-check dependencies",
        ATTEMPT_002_CANDIDATE_COMMIT,
        ATTEMPT_002_CANDIDATE_TREE,
        "Make exited `2`; the producer exited `1` with `fixed_compose_invalid`",
        ATTEMPT_002_RUN_ID,
        ATTEMPT_002_PROJECT,
        "gate and runtime were entered",
        "base-plus-overlay `tmpfs` list merge duplicated the `/tmp` mount target",
        "No Docker mutation/build/resource creation, provider call, API start, Node enrollment, "
        "Hermes invocation, credential output, or successful evidence occurred",
        "found zero residue, but cleanup is not claimed",
        "owner-only quarantined receipt and 663-file snapshot remain intentionally retained",
        ATTEMPT_002_CLOSURE_JSON.as_posix(),
        "validates that retained evidence directly and independently of Git ignore state",
        "current closure repair scope is exactly seven tracked paths",
        "three exact evidence-root child patterns",
        "do not create a broad `var` ignore",
        COMPOSE_REPAIR_COMMIT,
        COMPOSE_REPAIR_TREE,
        COMPOSE_REPAIR_REVIEW.as_posix(),
        "zero Critical, High, Medium, or Low findings and disposition `GO`",
        SOURCE_DIGESTS["base_compose_sha256"][1],
        SOURCE_DIGESTS["overlay_compose_sha256"][1],
        COMPOSE_REPAIR_PRODUCER_DIGEST,
        "/tmp:size=16m,mode=0700,uid=10002,gid=10002",
        ATTEMPT_003_DISPOSITION_JSON.as_posix(),
        "clean, single-parent immediate child",
        "exactly the seven-path control allowlist",
        ATTEMPT_003_CANDIDATE_COMMIT,
        ATTEMPT_003_CANDIDATE_TREE,
        "Make exited `2`; the producer exited `1` with `recovery_required`",
        ATTEMPT_003_RUN_ID,
        ATTEMPT_003_PROJECT,
        "Docker mutation and image-build phase was entered",
        "does not claim that an earlier primary error existed or assign a value to one",
        "may have replaced an earlier error or may have originated in cleanup itself",
        "bridge image-build failure a hypothesis, not a proven diagnosis",
        ATTEMPT_003_CLOSURE_JSON.as_posix(),
        "point-in-time exact-run-scoped read-only observation",
        "not current live truth, general Docker absence, completed cleanup, or authority",
        "validates the exact Attempt 002 and Attempt 003 retained receipts",
        IMAGE_RECOVERY_ID,
        IMAGE_RECOVERY_CANDIDATE_COMMIT,
        IMAGE_RECOVERY_CANDIDATE_TREE,
        IMAGE_RECOVERY_CLOSURE_COMMIT,
        IMAGE_RECOVERY_CLOSURE_TREE,
        IMAGE_RECOVERY_CONSUMPTION_RECEIPT.as_posix(),
        IMAGE_RECOVERY_CONSUMPTION_RECEIPT_DIGEST,
        "receipt remains durable consumption evidence",
        "Receipt deletion or mutation is not authorized",
        RUNTIME_NATIVE_REPAIR_COMMIT,
        RUNTIME_NATIVE_REPAIR_TREE,
        RUNTIME_NATIVE_REPAIR_REVIEW.as_posix(),
        "independent GPT-5.6 Sol xhigh read-only review",
        "Critical: 0, High: 0, Medium: 0, Low: 0",
        "exact-commit disposition `GO`",
        RUNTIME_NATIVE_BRIDGE_DIGEST,
        "runtime lineage",
        "exact inspected full image ID",
        "stable primary and cleanup failure classifications separately",
        ATTEMPT_004_ID,
        ATTEMPT_004_CANDIDATE_COMMIT,
        ATTEMPT_004_CANDIDATE_TREE,
        ATTEMPT_004_RUN_ID,
        ATTEMPT_004_PROJECT,
        "Both base and bridge builds completed",
        "base_services_start_failed",
        "owned_image_id_absence_probe_failed",
        "outward code was `recovery_required`",
        "verified narrow explanation",
        "separate read-only exact-run-scoped postcheck",
        "not a general Docker absence or cleanup-completed claim",
        "no image recovery is required or authorized",
        ATTEMPT_004_DISPOSITION_JSON.as_posix(),
        "exact eight-path closure allowlist",
        ATTEMPT_004_CLOSURE_COMMIT,
        ATTEMPT_004_CLOSURE_TREE,
        DIAGNOSTIC_REPAIR_COMMIT,
        DIAGNOSTIC_REPAIR_TREE,
        DIAGNOSTIC_REPAIR_REVIEW.as_posix(),
        "sha256:f484e2005f16b006c2251a53af728e6c62bee812d8c3616ccd059468e6069e14",
        "sha256:ef8b455cece020d76892e6ee19775bc0099414dbbff9ff9c24aa15128702bc33",
        "exact absent-image-ID probe accepts only the closed stdout set `{empty, newline}`",
        "fixed Compose `ps --all` diagnostic",
        "Combined output is bounded to 1,024 bytes",
        ATTEMPT_005_ID,
        ATTEMPT_005_CANDIDATE_COMMIT,
        ATTEMPT_005_CANDIDATE_TREE,
        ATTEMPT_005_RUN_ID,
        ATTEMPT_005_PROJECT,
        "primary and outward failure was `base_services_start_failed`",
        "API as `service_exited_nonzero`",
        "UI as `service_created`",
        "assigns no root cause",
        "successful in-run cleanup for the exact bound Attempt 005 resources",
        "point-in-time exact-run observations",
        "128-byte disposition, a 7,059-byte diagnostic, a 96,772-byte candidate manifest",
        "read-only 664-file exact candidate snapshot",
        ATTEMPT_005_DISPOSITION_JSON.as_posix(),
        "all four retained Attempt 002 through Attempt 005 receipt roots",
        "only the prior 336-byte",
        "exact eight-path closure allowlist",
        "separate reviewed API-exit diagnostic repair",
        API_CONTAINER_STATE_DIAGNOSTIC_COMMIT,
        API_CONTAINER_STATE_DIAGNOSTIC_TREE,
        API_CONTAINER_STATE_DIAGNOSTIC_REVIEW.as_posix(),
        API_CONTAINER_STATE_DIAGNOSTIC_REJECTED_001_COMMIT,
        API_CONTAINER_STATE_DIAGNOSTIC_REJECTED_001_TREE,
        API_CONTAINER_STATE_DIAGNOSTIC_REJECTED_002_COMMIT,
        API_CONTAINER_STATE_DIAGNOSTIC_REJECTED_002_TREE,
        API_CONTAINER_STATE_DIAGNOSTIC_PRODUCER_DIGEST,
        API_CONTAINER_STATE_DIAGNOSTIC_TEST_DIGEST,
        "base-service `up` fails",
        "`service_exited_nonzero`",
        "`ps --all --quiet ithildin-api`",
        "validated and bound 64-character container ID",
        "ten-second ceiling",
        "hard incremental 512-byte combined stdout-plus-stderr cap",
        "No raw output, container ID, daemon error, log, environment, mount, configuration, "
        "command, credential, prompt, provider content, or tool result is persisted",
        "bounded kill, wait, and poll attempts",
        "primary failure remains `base_services_start_failed`",
        "does not alter cleanup classification or cleanup behavior",
        "no root-cause claim",
        "does not claim Attempt 006 will succeed",
        ATTEMPT_006_ID,
        "committed diff to equal exactly",
        "execution budget is one",
        "`attempt_consumed` is false",
        "Any invocation outcome consumes Attempt 006",
        "immediate separate post-attempt disposition",
        ATTEMPT_006_CANDIDATE_COMMIT,
        ATTEMPT_006_CANDIDATE_TREE,
        ATTEMPT_006_RUN_ID,
        ATTEMPT_006_PROJECT,
        "API as `service_exited_nonzero`",
        "UI as `service_created`",
        "`api_application_exit_nonzero_no_engine_error`",
        "health `unhealthy`",
        "exact application root cause remains unknown",
        "cleanup failure list is empty",
        "`recovery_required` is false",
        "temporary Docker configuration cleaned",
        ATTEMPT_006_DISPOSITION_RECEIPT_DIGEST,
        ATTEMPT_006_DIAGNOSTIC_RECEIPT_DIGEST,
        ATTEMPT_006_MANIFEST_RECEIPT_DIGEST,
        ATTEMPT_006_DISPOSITION_JSON.as_posix(),
        "exact eight-path closure allowlist",
        "separately reviewed application-emitted closed startup-stage diagnostic",
        "must not scrape logs",
        "one server-owned",
        "`synthetic_read_review_v1`",
        "`max_cycles=1`",
        "Hermes may be invoked exactly once with no supplied",
        "Gateway mission detail and Gateway Agent Run detail/timeline",
        "actual Gateway truth is mission lifecycle `runner_reported_succeeded`, "
        "Agent Run record status `active`, and exactly two "
        "`tool.execution.completed` timeline events",
        "connected directly to `DEVNULL` when its subprocess is created",
        "reviewed runtime candidate remains byte-bound for Attempt 002",
        code_authorization.REVIEW_DOCUMENT,
        "does not prove absence of transient malicious same-UID mutation while Docker reads "
        "the build context",
        "host-local only at `http://127.0.0.1:11434`",
        "permission removal alone is insufficient",
        "If a validated Node ID exists but revocation is unavailable, invalid, or interrupted",
        "private recovery receipt is quarantined staged material, not successful published "
        "evidence",
        "There is no automatic retry",
        APPLICATION_STARTUP_STAGE_DIAGNOSTIC_COMMIT,
        APPLICATION_STARTUP_STAGE_DIAGNOSTIC_TREE,
        APPLICATION_STARTUP_STAGE_DIAGNOSTIC_REVIEW.as_posix(),
        "binds exactly six implementation and test paths",
        "12 closed startup stages",
        "capped at 256 bytes",
        "does not authorize log scraping",
        "does not establish root cause",
        "389 focused tests",
        "strict mypy",
        ATTEMPT_007_ID,
        "exact seven-path control allowlist",
        "budget is one",
        "`attempt_consumed` is false",
        "Any invocation outcome consumes Attempt 007",
        IMAGE_READABILITY_REPAIR_COMMIT,
        IMAGE_READABILITY_REPAIR_TREE,
        IMAGE_READABILITY_REPAIR_REVIEW.as_posix(),
        "binds exactly five repair and test paths",
        "`a+rX` cannot add write permission",
        "final runtime identities remain non-root",
        "valid unary tests with exactly one operand",
        "No Compose file or runtime snapshot behavior changed",
        "190 focused tests",
        ATTEMPT_008_ID,
        "Attempt 008 permits one exact supervised child",
        "exact seven-path control allowlist",
        "execution budget is one",
        "Any invocation outcome consumes Attempt 008",
        "Exactly five bounded live authority fields are true",
        "remaining 14 authority fields are false",
        ATTEMPT_008_CANDIDATE_COMMIT,
        ATTEMPT_008_CANDIDATE_TREE,
        ATTEMPT_008_RUN_ID,
        ATTEMPT_008_PROJECT,
        "`subprocess_output_rejected`",
        "`[enrollment_outcome_ambiguous]`",
        "`recovery_required`",
        "`NodeState.safe_summary()`",
        "`private_key_present`",
        "`private[_ -]?key`",
        "lexical scan before the enrollment JSON projection",
        "exact candidate source plus stage and return-path evidence",
        "not retained raw stdout proof",
        "Cleanup success is not claimed",
        "No image ID, run image reference, container, volume, network, runtime plaintext, "
        "or general Docker absence is claimed",
        ATTEMPT_008_DISPOSITION_RECEIPT_DIGEST,
        ATTEMPT_008_DIAGNOSTIC_RECEIPT_DIGEST,
        ATTEMPT_008_MANIFEST_RECEIPT_DIGEST,
        ATTEMPT_008_DISPOSITION_JSON.as_posix(),
        "exact eight-path closure allowlist",
        "separately reviewed enrollment-output projection repair, not a retry",
        "Attempts 001 through 008 are consumed",
        "all 19 authority fields are false",
        ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REJECTED_COMMIT,
        ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REJECTED_TREE,
        "one Medium finding (`M1`)",
        ENROLLMENT_OUTPUT_PROJECTION_REPAIR_COMMIT,
        ENROLLMENT_OUTPUT_PROJECTION_REPAIR_TREE,
        ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REVIEW.as_posix(),
        "Critical: 0, High: 0, Medium: 0, Low: 0",
        "captures subprocess streams as bytes",
        "strict UTF-8",
        "closed canonical projection with exactly three string fields",
        "`node_id`, `principal_id`, and `workspace_id`",
        "`principal_id == agent:node.{node_id}`",
        ATTEMPT_009_ID,
        "new separately authorized isolated attempt",
        "not a retry, cleanup, revocation, or reconciliation of Attempt 008",
        "generate a fresh run ID, Compose project, suffix, runtime root, receipt root, and "
        "evidence path",
        "preflight fails closed before live work",
        "exact seven-path control allowlist",
        "execution budget is one",
        "`attempt_consumed` is false",
        "Any invocation outcome consumes Attempt 009",
        "Exactly five bounded live authority fields are true",
        "remaining 14 authority fields are false",
        "24-tool/no-new-powers boundary is unchanged",
        "governed tool count remains exactly 24",
    ):
        if phrase not in normalized:
            failures.append(f"O4 execution authorization doc is missing phrase: {phrase}")


def _validate_producer_contract(
    document: str,
    contract: JsonObject,
    failures: list[str],
) -> None:
    normalized = " ".join(document.split())
    for phrase in (
        "Status: `entrypoint_repair_candidate_pending_exact_review_and_separate_attempt_"
        "disposition`",
        "candidate producer and reconciled assembler now implement this contract",
        "Attempt 001 is consumed after the failed file-path invocation",
        "make local-v1-lv1-003-o4-producer-run",
        "`uv run python -m scripts.local_v1_lv1_003_o4_producer`",
        "`uv run python scripts/local_v1_lv1_003_o4_producer.py` is not an authorized "
        "future entrypoint",
        "Importing the module does not execute `main`",
        "current consumed Attempt 001 disposition refuses this repaired entrypoint",
        "remains unusable for live producer evidence until this producer-and-assembler "
        "candidate receives independent exact review",
        "before it creates a runtime directory or performs Docker, API, provider, network",
        "One invocation has these exact ordered stages",
        "Create a unique `ithildin-local-v1-o4-<8 lowercase hex>`",
        "ordinary Node eligibility",
        "Admit exactly one server-owned `synthetic_read_review_v1`",
        "`max_cycles=1`",
        "route stdout and stderr directly to `DEVNULL`",
        "There is no automatic retry",
        "GET /missions/{mission_id}",
        "GET /runs/{run_id}",
        "Agent Run record status `active`",
        "exactly two distinct `tool.execution.completed` timeline events",
        "never trust runner-authored operation counts",
        "`image_artifact_inventory_digest`, never as an SBOM",
        "exact private snapshot with no-follow reads and a fixed size ceiling",
        "do not prove absence of transient malicious same-UID mutation while Docker reads "
        "the build context",
        "current discovery is exactly `pyproject.toml` and `uv.lock`, with zero tracked",
        "reconciled constrained-mission assembler and checker",
        "Container routing through `host.docker.internal` remains a runtime-only fact",
        "leaves `enrollment_outcome_ambiguous=true`, makes no revocation or absence claim",
        "writes and verifies `node-revocation-recovery.json`",
        "attempts the exact fixed-Node stop but skips project down",
        "Permission removal alone is never rollback success",
        "recovery_required",
        "Runtime-Only Facts Still Unproven",
    ):
        if phrase not in normalized:
            failures.append(f"O4 producer contract is missing phrase: {phrase}")
    stages = re.findall(r"(?m)^(\d+)\. ", document)
    if stages != [str(number) for number in range(1, 18)]:
        failures.append("O4 producer contract must contain exactly 17 ordered stages")
    document_digest = _digest(document)
    if document_digest != PRODUCER_CONTRACT_DIGEST:
        failures.append("O4 producer contract digest is invalid")
    if not _exact_json_equal(
        contract.get("producer_contract_sha256"),
        document_digest,
    ):
        failures.append("O4 producer contract digest binding is invalid")


def _validate_disposition(
    disposition: JsonObject,
    document: str,
    failures: list[str],
) -> None:
    expected: JsonObject = {
        "schema_version": "1",
        "record_type": "local_v1_lv1_003_o4_post_review_disposition",
        "record_status": "AUTHORIZE_SUPERVISED_ONE_ATTEMPT_IMMEDIATE_CHILD",
        "ticket_id": "LV1-003",
        "outcome_id": "O4",
        "candidate_parent_commit": HISTORICAL_CANDIDATE_PARENT_COMMIT,
        "candidate_parent_tree": HISTORICAL_CANDIDATE_PARENT_TREE,
        "reviewed_implementation_commit": REVIEWED_IMPLEMENTATION_COMMIT,
        "reviewed_implementation_tree": REVIEWED_IMPLEMENTATION_TREE,
        "producer_exact_review_path": PRODUCER_EXACT_REVIEW.as_posix(),
        "producer_exact_review_sha256": PRODUCER_EXACT_REVIEW_DIGEST,
        "code_authorization_path": code_authorization.AUTHORIZATION,
        "code_authorization_commit": CODE_AUTHORIZATION_COMMIT,
        "code_authorization_tree": CODE_AUTHORIZATION_TREE,
        "code_authorization_record_sha256": CODE_AUTHORIZATION_RECORD_DIGEST,
        "producer_contract_sha256": HISTORICAL_PRODUCER_CONTRACT_DIGEST,
        "execution_candidate_binding": {
            "mode": "dynamic_current_head_after_all_checks",
            "required_parent_relation": "single_immediate_child_of_candidate_parent",
            "clean_checkout_required": True,
            "static_child_commit_claimed": False,
            "static_child_tree_claimed": False,
            "runtime_byte_parity_commit": REVIEWED_IMPLEMENTATION_COMMIT,
            "changed_paths_must_equal_control_allowlist": True,
        },
        "control_path_allowlist": cast(
            list[JsonValue],
            HISTORICAL_CONTROL_PATH_ALLOWLIST,
        ),
        "attempt_contract": {
            "maximum_supervised_invocations": 1,
            "custody": "central_manager_supervised_local_invocation",
            "concurrent_invocations_authorized": False,
            "automatic_retry_authorized": False,
            "post_attempt_rerun_authorized": False,
            "immediate_post_attempt_disposition_required": True,
            "persistent_cross_process_budget_consumption_claimed": False,
            "prior_attempt_detection": (
                "retained_exact_local_evidence_only_not_tamper_proof_or_atomic_consumption"
            ),
            "prior_attempt_roots": cast(list[JsonValue], PRIOR_ATTEMPT_ROOTS),
        },
        "authority": HISTORICAL_AUTHORITY,
    }
    if not _exact_json_equal(disposition, expected):
        failures.append("O4 post-review disposition is not closed and exact")
    normalized = " ".join(document.split())
    for phrase in (
        "AUTHORIZE_SUPERVISED_ONE_ATTEMPT_IMMEDIATE_CHILD",
        HISTORICAL_CANDIDATE_PARENT_COMMIT,
        REVIEWED_IMPLEMENTATION_COMMIT,
        "six-path control allowlist",
        "No future child commit or tree is stated here",
        "one central-manager-supervised local producer invocation",
        "does not implement or claim atomic, tamper-proof, persistent cross-process budget "
        "consumption",
        "No concurrent invocation, automatic retry, or post-attempt rerun is authorized",
        "requires an immediate new post-attempt disposition",
        "Only these five authority bits are true",
        "governed tool count remains exactly 24",
    ):
        if phrase not in normalized:
            failures.append(f"O4 post-review disposition doc is missing phrase: {phrase}")


def _validate_attempt_001_disposition(
    disposition: JsonObject,
    document: str,
    failures: list[str],
) -> None:
    expected: JsonObject = {
        "schema_version": "1",
        "record_type": "local_v1_lv1_003_o4_attempt_disposition",
        "record_status": "ATTEMPT_CONSUMED_PRE_GATE_IMPORT_FAILURE",
        "ticket_id": "LV1-003",
        "outcome_id": "O4",
        "attempt_id": ATTEMPT_001_ID,
        "attempt_number": 1,
        "attempted_candidate_commit": ATTEMPT_001_CANDIDATE_COMMIT,
        "attempted_candidate_tree": ATTEMPT_001_CANDIDATE_TREE,
        "attempted_candidate_clean": True,
        "attempted_authorization_contract_sha256": (ATTEMPT_001_AUTHORIZATION_CONTRACT_DIGEST),
        "invocation": {
            "command": ATTEMPT_001_COMMAND,
            "exit_code": 1,
            "classification": "PRE_GATE_MODULE_IMPORT_FAILURE",
            "exception_type": "ModuleNotFoundError",
            "exception_message": "No module named 'scripts'",
            "failure_location": "scripts/local_v1_lv1_003_o4_producer.py:36",
            "module_import_started": True,
            "gate_authorization_entered": False,
            "producer_runtime_entered": False,
        },
        "observed_root_absence": {
            "observation_method": "read_only_path_absence_check_after_failed_invocation",
            "roots": [{"path": path, "exists": False} for path in PRIOR_ATTEMPT_ROOTS],
        },
        "external_action_observation": {
            "runtime_created": False,
            "docker_action_performed": False,
            "ollama_or_provider_action_performed": False,
            "api_action_performed": False,
            "node_action_performed": False,
            "hermes_action_performed": False,
            "credential_action_performed": False,
            "network_journey_action_performed": False,
            "evidence_action_performed": False,
        },
        "attempt_contract": {
            "attempt_consumed": True,
            "retry_authorized": False,
            "automatic_retry_authorized": False,
            "post_failure_execution_authorized": False,
            "separately_reviewed_repair_candidate_required": True,
            "separate_post_review_execution_disposition_required": True,
        },
        "closure_candidate_binding": {
            "closure_commit_claimed": False,
            "closure_tree_claimed": False,
            "descendant_closure_commit_allowed": True,
        },
        "authority": CLOSED_AUTHORITY,
    }
    if not _exact_json_equal(disposition, expected):
        failures.append("O4 Attempt 001 disposition is not closed and exact")
    normalized = " ".join(document.split())
    for phrase in (
        "Status: `ATTEMPT_CONSUMED_PRE_GATE_IMPORT_FAILURE`",
        ATTEMPT_001_ID,
        ATTEMPT_001_CANDIDATE_COMMIT,
        ATTEMPT_001_CANDIDATE_TREE,
        ATTEMPT_001_COMMAND,
        "exited `1` during module import",
        "`ModuleNotFoundError: No module named 'scripts'`",
        "authorization gate was not entered and producer runtime was not entered",
        "all three exact roots absent",
        "no runtime creation, Docker action, Ollama or model provider action, API action, "
        "Node action, Hermes action, credential action, network journey action, or evidence "
        "action",
        "attempt budget is now zero and all 19 authority fields are false",
        "A retry requires a repaired candidate, independent exact review of that candidate, "
        "and a separate post-review execution disposition",
        "does not state or derive its own future closure commit or tree",
    ):
        if phrase not in normalized:
            failures.append(f"O4 Attempt 001 disposition doc is missing phrase: {phrase}")


def _validate_entrypoint_repair_review(
    document: str,
    failures: list[str],
) -> None:
    normalized = " ".join(document.split())
    for phrase in (
        "Status: `GO`",
        "independent Sol xhigh read-only review",
        ENTRYPOINT_REPAIR_COMMIT,
        ENTRYPOINT_REPAIR_TREE,
        ENTRYPOINT_REPAIR_BASE_COMMIT,
        "changes exactly these seven paths",
        PRODUCER_MODULE_INVOCATION,
        ATTEMPT_002_OPERATOR_COMMAND,
        "Critical: 0",
        "High: 0",
        "Medium: 0",
        "Low: 0",
        "exact-commit disposition is `GO`",
        "permits preparation of a separate Attempt 002 execution disposition only",
        "does not modify the Attempt 001 record",
    ):
        if phrase not in normalized:
            failures.append(f"O4 entrypoint repair review is missing phrase: {phrase}")
    if _digest(document) != ENTRYPOINT_REPAIR_REVIEW_DIGEST:
        failures.append("O4 entrypoint repair review digest is invalid")


def _validate_attempt_002_disposition(
    disposition: JsonObject,
    document: str,
    failures: list[str],
) -> None:
    expected: JsonObject = {
        "schema_version": "1",
        "record_type": "local_v1_lv1_003_o4_attempt_disposition",
        "record_status": "AUTHORIZE_SUPERVISED_ONE_ATTEMPT_IMMEDIATE_CHILD",
        "ticket_id": "LV1-003",
        "outcome_id": "O4",
        "attempt_id": ATTEMPT_002_ID,
        "candidate_parent_commit": ENTRYPOINT_REPAIR_COMMIT,
        "candidate_parent_tree": ENTRYPOINT_REPAIR_TREE,
        "repair_parent_commit": ENTRYPOINT_REPAIR_BASE_COMMIT,
        "reviewed_runtime_commit": REVIEWED_IMPLEMENTATION_COMMIT,
        "entrypoint_repair_review_path": ENTRYPOINT_REPAIR_REVIEW.as_posix(),
        "entrypoint_repair_review_sha256": ENTRYPOINT_REPAIR_REVIEW_DIGEST,
        "attempt_001_history": {
            "attempted_candidate_commit": ATTEMPT_001_CANDIDATE_COMMIT,
            "record_status": "ATTEMPT_CONSUMED_PRE_GATE_IMPORT_FAILURE",
            "disposition_json_path": ATTEMPT_001_DISPOSITION_JSON.as_posix(),
            "disposition_json_sha256": ATTEMPT_001_DISPOSITION_JSON_DIGEST,
            "disposition_document_path": ATTEMPT_001_DISPOSITION_DOCUMENT.as_posix(),
            "disposition_document_sha256": ATTEMPT_001_DISPOSITION_DOCUMENT_DIGEST,
            "consumed": True,
            "retry_authorized": False,
        },
        "operator_command": ATTEMPT_002_OPERATOR_COMMAND,
        "module_command": PRODUCER_MODULE_INVOCATION,
        "failed_file_path_command": FAILED_FILE_PATH_INVOCATION,
        "failed_file_path_command_authorized": False,
        "execution_candidate_binding": {
            "mode": "dynamic_current_head_after_all_checks",
            "required_parent_relation": "single_immediate_child_of_candidate_parent",
            "clean_checkout_required": True,
            "static_child_commit_claimed": False,
            "static_child_tree_claimed": False,
            "runtime_byte_parity_commit": REVIEWED_IMPLEMENTATION_COMMIT,
            "repair_byte_parity_commit": ENTRYPOINT_REPAIR_COMMIT,
            "changed_paths_must_equal_control_allowlist": True,
        },
        "control_path_allowlist": cast(list[JsonValue], CONTROL_PATH_ALLOWLIST),
        "attempt_contract": {
            "maximum_supervised_invocations": 1,
            "custody": "central_manager_supervised_local_invocation",
            "concurrent_invocations_authorized": False,
            "automatic_retry_authorized": False,
            "post_attempt_rerun_authorized": False,
            "immediate_post_attempt_disposition_required": True,
            "persistent_cross_process_budget_consumption_claimed": False,
            "prior_attempt_detection": (
                "retained_exact_local_evidence_only_not_tamper_proof_or_atomic_consumption"
            ),
            "prior_attempt_roots": cast(list[JsonValue], PRIOR_ATTEMPT_ROOTS),
        },
        "authority": ATTEMPT_002_AUTHORITY,
    }
    if not _exact_json_equal(disposition, expected):
        failures.append("O4 Attempt 002 disposition is not closed and exact")
    normalized = " ".join(document.split())
    for phrase in (
        "Status: `AUTHORIZE_SUPERVISED_ONE_ATTEMPT_IMMEDIATE_CHILD`",
        ATTEMPT_002_ID,
        ENTRYPOINT_REPAIR_COMMIT,
        ENTRYPOINT_REPAIR_TREE,
        ENTRYPOINT_REPAIR_BASE_COMMIT,
        "zero Critical, High, Medium, or Low findings",
        "No future child commit or tree is stated here",
        "clean, single-parent immediate child",
        "exactly the seven-path control allowlist",
        REVIEWED_IMPLEMENTATION_COMMIT,
        ATTEMPT_002_OPERATOR_COMMAND,
        PRODUCER_MODULE_INVOCATION,
        FAILED_FILE_PATH_INVOCATION,
        "Attempt 001 remains `ATTEMPT_CONSUMED_PRE_GATE_IMPORT_FAILURE`",
        "Existing roots must be no-follow owner-owned `0700` directories and empty",
        "does not implement or claim atomic, tamper-proof, persistent cross-process budget "
        "consumption",
        "requires an immediate new post-attempt disposition",
        "Exactly five authority fields are true",
        "remaining 14 authority fields are false",
        "governed tool count remains exactly 24",
    ):
        if phrase not in normalized:
            failures.append(f"O4 Attempt 002 disposition doc is missing phrase: {phrase}")


def _validate_attempt_002_closure(
    closure: JsonObject,
    document: str,
    failures: list[str],
) -> None:
    expected: JsonObject = {
        "schema_version": "1",
        "record_type": "local_v1_lv1_003_o4_attempt_closure",
        "record_status": "ATTEMPT_002_CONSUMED_FIXED_COMPOSE_INVALID",
        "ticket_id": "LV1-003",
        "outcome_id": "O4",
        "attempt_id": ATTEMPT_002_ID,
        "attempted_candidate_commit": ATTEMPT_002_CANDIDATE_COMMIT,
        "attempted_candidate_tree": ATTEMPT_002_CANDIDATE_TREE,
        "operator_command": ATTEMPT_002_OPERATOR_COMMAND,
        "module_command": PRODUCER_MODULE_INVOCATION,
        "make_exit_code": 2,
        "producer_exit_code": 1,
        "failure_code": "fixed_compose_invalid",
        "run_id": ATTEMPT_002_RUN_ID,
        "compose_project": ATTEMPT_002_PROJECT,
        "execution_boundary": {
            "gate_entered": True,
            "producer_runtime_entered": True,
            "runtime_directory_created": True,
            "receipt_directory_created": True,
            "candidate_snapshot_created": True,
            "docker_daemon_version_queried": True,
            "docker_compose_version_queried": True,
            "base_compose_config_quiet_succeeded": True,
            "fixed_compose_config_quiet_succeeded": False,
        },
        "diagnosis": {
            "diagnosis_only_command_authorized": False,
            "observed_error": (
                "services.ithildin-node.tmpfs[1]: target /tmp already mounted as "
                "services.ithildin-node.tmpfs[0]"
            ),
            "root_cause": "base_and_overlay_tmpfs_list_merge_duplicates_tmp_target",
            "overlay_repair_included": False,
        },
        "external_action_observation": {
            "docker_mutation_performed": False,
            "image_build_performed": False,
            "container_created": False,
            "volume_created": False,
            "network_created": False,
            "image_created": False,
            "ollama_or_provider_called": False,
            "api_service_started": False,
            "node_enrollment_performed": False,
            "hermes_invoked": False,
            "credential_output_emitted": False,
            "successful_evidence_created": False,
        },
        "read_only_residue_observation": {
            "exact_project_label_containers": 0,
            "exact_project_label_volumes": 0,
            "exact_project_label_networks": 0,
            "exact_run_specific_images": 0,
            "cleanup_completed_claimed": False,
            "general_docker_absence_claimed": False,
        },
        "retained_receipt": {
            "receipt_root": f"var/local-v1-lv1-003-o4-receipts/{ATTEMPT_002_RUN_ID}",
            "receipt_root_mode": "0700",
            "disposition_path": (
                f"var/local-v1-lv1-003-o4-receipts/{ATTEMPT_002_RUN_ID}/disposition.json"
            ),
            "disposition_mode": "0600",
            "disposition_status": "quarantined_not_published",
            "disposition_sha256": (
                "sha256:653e7cb4a656db714769cad329b49c55a194bb5223c911274a57c4a7abbef44b"
            ),
            "candidate_manifest_path": (
                f"var/local-v1-lv1-003-o4-receipts/{ATTEMPT_002_RUN_ID}/candidate-manifest.json"
            ),
            "candidate_manifest_mode": "0600",
            "candidate_manifest_size_bytes": 96628,
            "candidate_manifest_sha256": (
                "sha256:ac9a119a083a786cfcead9cd5600a43350bc78cd2f500ffcc59f4969e34f087b"
            ),
            "candidate_snapshot_path": (
                f"var/local-v1-lv1-003-o4-receipts/{ATTEMPT_002_RUN_ID}/candidate"
            ),
            "candidate_snapshot_mode": "0500",
            "candidate_snapshot_file_count": 663,
            "published_report_root_exists": False,
        },
        "runtime_posture": {
            "run_directory_exists": False,
            "runtime_plaintext_exists": False,
            "runtime_base_exists": True,
            "runtime_base_mode": "0700",
            "runtime_base_empty": True,
        },
        "tracked_closure_scope": cast(
            list[JsonValue],
            CLOSURE_CONTROL_PATH_ALLOWLIST,
        ),
        "attempt_contract": {
            "attempt_consumed": True,
            "retry_authorized": False,
            "automatic_retry_authorized": False,
            "post_failure_execution_authorized": False,
            "separately_repaired_overlay_candidate_required": True,
            "independent_exact_review_required": True,
            "separate_new_attempt_disposition_required": True,
        },
        "authority": CLOSED_AUTHORITY,
    }
    if not _exact_json_equal(closure, expected):
        failures.append("O4 Attempt 002 closure is not closed and exact")
    normalized = " ".join(document.split())
    for phrase in (
        "Status: `ATTEMPT_002_CONSUMED_FIXED_COMPOSE_INVALID`",
        ATTEMPT_002_CANDIDATE_COMMIT,
        ATTEMPT_002_CANDIDATE_TREE,
        ATTEMPT_002_OPERATOR_COMMAND,
        PRODUCER_MODULE_INVOCATION,
        "Make exited `2`",
        "producer exited `1` with refusal code `fixed_compose_invalid`",
        ATTEMPT_002_RUN_ID,
        ATTEMPT_002_PROJECT,
        "gate and producer runtime were entered",
        "fixed-overlay Compose config validation failed",
        "target /tmp already mounted",
        "does not repair the overlay",
        "No Docker mutation, image build, container, volume, network, or image creation occurred",
        "zero containers, volumes, networks, and images",
        "not a claim that cleanup ran",
        "runtime run directory and runtime plaintext are absent",
        "quarantined_not_published",
        "sha256:653e7cb4a656db714769cad329b49c55a194bb5223c911274a57c4a7abbef44b",
        "sha256:ac9a119a083a786cfcead9cd5600a43350bc78cd2f500ffcc59f4969e34f087b",
        "contains 663 files",
        "no-follow owner identity and exact modes, sizes, digests, manifest paths, "
        "snapshot bytes, and directory contents",
        "current closure repair scope is exactly seven tracked paths",
        "three exact evidence-root child patterns",
        "without using a broad `var` ignore",
        "all 19 authority fields are false",
        "separately repaired overlay candidate, independent exact review, and a separate "
        "new-attempt disposition",
    ):
        if phrase not in normalized:
            failures.append(f"O4 Attempt 002 closure doc is missing phrase: {phrase}")


def _validate_compose_repair_review(
    document: str,
    failures: list[str],
) -> None:
    normalized = " ".join(document.split())
    for phrase in (
        "Status: `GO`",
        "independent Sol xhigh read-only review",
        COMPOSE_REPAIR_COMMIT,
        COMPOSE_REPAIR_TREE,
        "changes exactly these five paths",
        "/tmp:size=16m,mode=0700,uid=10002,gid=10002",
        SOURCE_DIGESTS["base_compose_sha256"][1],
        SOURCE_DIGESTS["overlay_compose_sha256"][1],
        COMPOSE_REPAIR_PRODUCER_DIGEST,
        "Critical: 0",
        "High: 0",
        "Medium: 0",
        "Low: 0",
        "exact-commit disposition is `GO`",
        "accompanying closed Attempt 003 control disposition",
        "does not itself execute Attempt 003",
        "24-tool/no-new-powers boundary",
    ):
        if phrase not in normalized:
            failures.append(f"O4 Compose repair review is missing phrase: {phrase}")
    if _digest(document) != COMPOSE_REPAIR_REVIEW_DIGEST:
        failures.append("O4 Compose repair review digest is invalid")


def _validate_attempt_003_disposition(
    disposition: JsonObject,
    document: str,
    failures: list[str],
) -> None:
    expected: JsonObject = {
        "schema_version": "1",
        "record_type": "local_v1_lv1_003_o4_attempt_disposition",
        "record_status": "AUTHORIZE_SUPERVISED_ONE_ATTEMPT_IMMEDIATE_CHILD",
        "ticket_id": "LV1-003",
        "outcome_id": "O4",
        "attempt_id": ATTEMPT_003_ID,
        "candidate_parent_commit": COMPOSE_REPAIR_COMMIT,
        "candidate_parent_tree": COMPOSE_REPAIR_TREE,
        "compose_repair_review_path": COMPOSE_REPAIR_REVIEW.as_posix(),
        "compose_repair_review_sha256": COMPOSE_REPAIR_REVIEW_DIGEST,
        "repaired_source_digests": {
            "base_compose_sha256": SOURCE_DIGESTS["base_compose_sha256"][1],
            "overlay_compose_sha256": SOURCE_DIGESTS["overlay_compose_sha256"][1],
            "producer_source_sha256": COMPOSE_REPAIR_PRODUCER_DIGEST,
        },
        "attempt_001_history": {
            "attempted_candidate_commit": ATTEMPT_001_CANDIDATE_COMMIT,
            "record_status": "ATTEMPT_CONSUMED_PRE_GATE_IMPORT_FAILURE",
            "disposition_json_sha256": ATTEMPT_001_DISPOSITION_JSON_DIGEST,
            "disposition_document_sha256": ATTEMPT_001_DISPOSITION_DOCUMENT_DIGEST,
            "consumed": True,
            "retry_authorized": False,
        },
        "attempt_002_history": {
            "attempted_candidate_commit": ATTEMPT_002_CANDIDATE_COMMIT,
            "attempted_candidate_tree": ATTEMPT_002_CANDIDATE_TREE,
            "record_status": "ATTEMPT_002_CONSUMED_FIXED_COMPOSE_INVALID",
            "closure_json_sha256": ATTEMPT_002_CLOSURE_JSON_DIGEST,
            "closure_document_sha256": ATTEMPT_002_CLOSURE_DOCUMENT_DIGEST,
            "retained_disposition_sha256": (ATTEMPT_002_DISPOSITION_RECEIPT_DIGEST),
            "retained_manifest_sha256": ATTEMPT_002_MANIFEST_RECEIPT_DIGEST,
            "consumed": True,
            "retry_authorized": False,
        },
        "operator_command": ATTEMPT_002_OPERATOR_COMMAND,
        "module_command": PRODUCER_MODULE_INVOCATION,
        "execution_candidate_binding": {
            "mode": "dynamic_current_head_after_all_checks",
            "required_parent_relation": "single_immediate_child_of_candidate_parent",
            "clean_checkout_required": True,
            "static_child_commit_claimed": False,
            "static_child_tree_claimed": False,
            "reviewed_repair_byte_parity_commit": COMPOSE_REPAIR_COMMIT,
            "changed_paths_must_equal_control_allowlist": True,
        },
        "control_path_allowlist": cast(
            list[JsonValue],
            ATTEMPT_003_CONTROL_PATH_ALLOWLIST,
        ),
        "prior_attempt_evidence_contract": {
            "attempt_002_retained_evidence_required": True,
            "attempt_002_receipt_run_id": ATTEMPT_002_RUN_ID,
            "attempt_002_receipt_entries_exact": True,
            "runtime_base_must_be_empty": True,
            "attempt_002_runtime_run_absent": True,
            "attempt_002_published_report_absent": True,
            "unknown_or_additional_attempt_roots_authorized": False,
        },
        "attempt_contract": {
            "maximum_supervised_invocations": 1,
            "custody": "central_manager_supervised_local_invocation",
            "concurrent_invocations_authorized": False,
            "automatic_retry_authorized": False,
            "post_attempt_rerun_authorized": False,
            "immediate_post_attempt_disposition_required": True,
            "persistent_cross_process_budget_consumption_claimed": False,
        },
        "authority": HISTORICAL_AUTHORITY,
    }
    if not _exact_json_equal(disposition, expected):
        failures.append("O4 Attempt 003 disposition is not closed and exact")
    normalized = " ".join(document.split())
    for phrase in (
        "Status: `AUTHORIZE_SUPERVISED_ONE_ATTEMPT_IMMEDIATE_CHILD`",
        ATTEMPT_003_ID,
        COMPOSE_REPAIR_COMMIT,
        COMPOSE_REPAIR_TREE,
        "zero Critical, High, Medium, or Low findings",
        "No future child commit or tree is stated here",
        "clean, single-parent immediate child",
        "exact seven-path control allowlist",
        "all 663 snapshot files",
        "exact Attempt 002 receipt is allowed and required",
        "unknown or additional receipt run",
        "does not claim atomic, tamper-proof, persistent cross-process budget consumption",
        "Exactly five authority fields are true",
        "remaining 14 authority fields are false",
        "governed tool count remains exactly 24",
    ):
        if phrase not in normalized:
            failures.append(f"O4 Attempt 003 disposition doc is missing phrase: {phrase}")


def _validate_attempt_003_closure(
    closure: JsonObject,
    document: str,
    failures: list[str],
) -> None:
    expected: JsonObject = {
        "schema_version": "1",
        "record_type": "local_v1_lv1_003_o4_attempt_closure",
        "record_status": "ATTEMPT_003_CONSUMED_RECOVERY_REQUIRED",
        "ticket_id": "LV1-003",
        "outcome_id": "O4",
        "attempt_id": ATTEMPT_003_ID,
        "attempted_candidate_commit": ATTEMPT_003_CANDIDATE_COMMIT,
        "attempted_candidate_tree": ATTEMPT_003_CANDIDATE_TREE,
        "operator_command": ATTEMPT_002_OPERATOR_COMMAND,
        "module_command": PRODUCER_MODULE_INVOCATION,
        "make_exit_code": 2,
        "producer_exit_code": 1,
        "failure_code": "recovery_required",
        "run_id": ATTEMPT_003_RUN_ID,
        "compose_project": ATTEMPT_003_PROJECT,
        "execution_boundary": {
            "gate_entered": True,
            "producer_runtime_entered": True,
            "runtime_directory_created": True,
            "receipt_directory_created": True,
            "candidate_snapshot_created": True,
            "docker_mutation_phase_entered": True,
            "image_build_phase_entered": True,
            "base_image_outputs_observed": True,
            "later_runtime_phase_entered_claimed": False,
            "cleanup_completed": False,
        },
        "diagnosis": {
            "diagnosis_only_command_authorized": False,
            "primary_error_presence_known": False,
            "primary_error_value_known": False,
            "final_recovery_required_may_have_replaced_primary_or_originated_in_cleanup": (True),
            "bridge_image_build_failure_hypothesis": True,
            "bridge_image_build_failure_proven": False,
            "recovery_failure_root_cause": "unknown",
            "repair_included": False,
        },
        "execution_claim_limits": {
            "provider_call_absence_claimed": False,
            "api_service_start_absence_claimed": False,
            "node_enrollment_absence_claimed": False,
            "hermes_invocation_absence_claimed": False,
            "credential_output_absence_claimed": False,
            "successful_evidence_created": False,
        },
        "read_only_residue_observation": {
            "observation_scope": "point_in_time_exact_run_scoped_post_attempt",
            "exact_project_label_containers": 0,
            "exact_project_label_volumes": 0,
            "exact_project_label_networks": 0,
            "hermes_run_image_present": False,
            "retained_run_images": [
                {
                    "service": "ithildin-api",
                    "reference": "ithildin/api-o4:6460809b",
                    "image_id": (
                        "sha256:19dc658884e9298b7966e5fb10c80874afaa33956e565b55dd0a30e8a02bd5d6"
                    ),
                    "platform": "linux/arm64",
                    "project_label": ("com.docker.compose.project=ithildin-local-v1-o4-6460809b"),
                    "service_label": "com.docker.compose.service=ithildin-api",
                    "sole_tag_at_observation": True,
                    "container_count_at_observation": 0,
                },
                {
                    "service": "ithildin-ui",
                    "reference": "ithildin/ui-o4:6460809b",
                    "image_id": (
                        "sha256:4b530eb0fc350c433089d88ddd75d03042e633a5b23a0fdeaaeb77c58f75b6b7"
                    ),
                    "platform": "linux/arm64",
                    "project_label": ("com.docker.compose.project=ithildin-local-v1-o4-6460809b"),
                    "service_label": "com.docker.compose.service=ithildin-ui",
                    "sole_tag_at_observation": True,
                    "container_count_at_observation": 0,
                },
                {
                    "service": "ithildin-node",
                    "reference": "ithildin/node-o4:6460809b",
                    "image_id": (
                        "sha256:0d85000f6172508554524f276d4051170e53a6c3fc79cbc5dc1b0c051b682c81"
                    ),
                    "platform": "linux/arm64",
                    "project_label": ("com.docker.compose.project=ithildin-local-v1-o4-6460809b"),
                    "service_label": "com.docker.compose.service=ithildin-node",
                    "sole_tag_at_observation": True,
                    "container_count_at_observation": 0,
                },
            ],
            "images_removed": False,
            "cleanup_completed_claimed": False,
            "general_docker_absence_claimed": False,
            "current_live_truth_claimed": False,
        },
        "retained_receipt": {
            "receipt_root": (f"var/local-v1-lv1-003-o4-receipts/{ATTEMPT_003_RUN_ID}"),
            "receipt_root_mode": "0700",
            "disposition_path": (
                f"var/local-v1-lv1-003-o4-receipts/{ATTEMPT_003_RUN_ID}/disposition.json"
            ),
            "disposition_mode": "0600",
            "disposition_size_bytes": len(ATTEMPT_003_DISPOSITION_BYTES),
            "disposition_status": "quarantined_not_published",
            "disposition_sha256": ATTEMPT_003_DISPOSITION_RECEIPT_DIGEST,
            "candidate_manifest_path": (
                f"var/local-v1-lv1-003-o4-receipts/{ATTEMPT_003_RUN_ID}/candidate-manifest.json"
            ),
            "candidate_manifest_mode": "0600",
            "candidate_manifest_size_bytes": ATTEMPT_003_MANIFEST_SIZE,
            "candidate_manifest_sha256": ATTEMPT_003_MANIFEST_RECEIPT_DIGEST,
            "candidate_snapshot_path": (
                f"var/local-v1-lv1-003-o4-receipts/{ATTEMPT_003_RUN_ID}/candidate"
            ),
            "candidate_snapshot_mode": "0500",
            "candidate_snapshot_file_count": ATTEMPT_003_SNAPSHOT_FILE_COUNT,
            "published_report_base_exists": False,
        },
        "runtime_posture": {
            "run_directory_exists": False,
            "runtime_plaintext_exists": False,
            "runtime_base_exists": True,
            "runtime_base_mode": "0700",
            "runtime_base_empty": True,
        },
        "tracked_closure_scope": cast(
            list[JsonValue],
            ATTEMPT_003_CLOSURE_CONTROL_PATH_ALLOWLIST,
        ),
        "attempt_contract": {
            "attempt_consumed": True,
            "retry_authorized": False,
            "automatic_retry_authorized": False,
            "post_failure_execution_authorized": False,
            "recovery_action_authorized": False,
            "image_removal_authorized": False,
            "separate_recovery_disposition_required": True,
            "independent_exact_review_required": True,
            "separate_new_attempt_disposition_required": True,
        },
        "authority": CLOSED_AUTHORITY,
    }
    if not _exact_json_equal(closure, expected):
        failures.append("O4 Attempt 003 closure is not closed and exact")
    normalized = " ".join(document.split())
    for phrase in (
        "Status: `ATTEMPT_003_CONSUMED_RECOVERY_REQUIRED`",
        ATTEMPT_003_ID,
        ATTEMPT_003_CANDIDATE_COMMIT,
        ATTEMPT_003_CANDIDATE_TREE,
        "Make exited `2`",
        "producer exited `1` with refusal code `recovery_required`",
        ATTEMPT_003_RUN_ID,
        ATTEMPT_003_PROJECT,
        "Docker mutation and image-build phase was entered",
        "Cleanup did not complete",
        "does not claim that an earlier primary error existed",
        "does not claim a value for one",
        "may have replaced an earlier error or may have originated in cleanup itself",
        "hypothesis, not a proven diagnosis",
        "point-in-time observation only",
        "not current live truth",
        ATTEMPT_003_DISPOSITION_RECEIPT_DIGEST,
        ATTEMPT_003_MANIFEST_RECEIPT_DIGEST,
        "directly reads both Attempt 002 and Attempt 003 retained receipts",
        "exactly six tracked paths",
        "all 19 authority fields are false",
        "Release, promotion, production, and UAT remain false",
    ):
        if phrase not in normalized:
            failures.append(f"O4 Attempt 003 closure doc is missing phrase: {phrase}")


def _validate_image_recovery_history(
    authorization: JsonObject,
    authorization_document: str,
    closure: JsonObject,
    closure_document: str,
    failures: list[str],
) -> None:
    expected_receipt: JsonObject = {
        "path": IMAGE_RECOVERY_CONSUMPTION_RECEIPT.as_posix(),
        "runtime_base_mode": "0700",
        "runtime_base_entries": [IMAGE_RECOVERY_CONSUMPTION_RECEIPT_NAME],
        "receipt_mode": "0600",
        "receipt_size_bytes": len(IMAGE_RECOVERY_CONSUMPTION_RECEIPT_BYTES),
        "receipt_sha256": IMAGE_RECOVERY_CONSUMPTION_RECEIPT_DIGEST,
        "receipt_candidate_commit": IMAGE_RECOVERY_CANDIDATE_COMMIT,
        "receipt_candidate_tree": IMAGE_RECOVERY_CANDIDATE_TREE,
        "receipt_status": "consumed_before_docker_inspection",
        "receipt_retry_authorized": False,
        "receipt_retained": True,
        "receipt_removal_authorized": False,
    }
    if (
        authorization.get("record_status") != "ATTEMPT_003_IMAGE_RECOVERY_CLOSED_NO_AUTHORITY"
        or authorization.get("recovery_id") != IMAGE_RECOVERY_ID
        or authorization.get("recovery_candidate_commit") != IMAGE_RECOVERY_CANDIDATE_COMMIT
        or authorization.get("recovery_candidate_tree") != IMAGE_RECOVERY_CANDIDATE_TREE
        or not _exact_json_equal(
            authorization.get("durable_consumption_receipt"),
            expected_receipt,
        )
        or authorization.get("recovery_attempt_budget") != 0
        or authorization.get("retry_authorized") is not False
        or not _exact_json_equal(
            authorization.get("o4_authority"),
            CLOSED_AUTHORITY,
        )
    ):
        failures.append("O4 image recovery authorization closure is not exact")
    closure_receipt = closure.get("durable_consumption_receipt")
    if (
        closure.get("record_status") != "RECOVERY_COMPLETED_EXACT_IMAGE_REMOVAL_CLOSED"
        or closure.get("recovery_id") != IMAGE_RECOVERY_ID
        or closure.get("recovery_candidate_commit") != IMAGE_RECOVERY_CANDIDATE_COMMIT
        or closure.get("recovery_candidate_tree") != IMAGE_RECOVERY_CANDIDATE_TREE
        or not isinstance(closure_receipt, dict)
        or closure_receipt.get("path") != IMAGE_RECOVERY_CONSUMPTION_RECEIPT.as_posix()
        or closure_receipt.get("receipt_size_bytes")
        != len(IMAGE_RECOVERY_CONSUMPTION_RECEIPT_BYTES)
        or closure_receipt.get("receipt_sha256") != IMAGE_RECOVERY_CONSUMPTION_RECEIPT_DIGEST
        or closure_receipt.get("receipt_retained") is not True
        or closure_receipt.get("receipt_removal_authorized") is not False
        or closure.get("recovery_attempt_budget") != 0
        or closure.get("retry_authorized") is not False
        or not _exact_json_equal(closure.get("o4_authority"), CLOSED_AUTHORITY)
    ):
        failures.append("O4 image recovery result closure is not exact")
    for label, document, phrases in (
        (
            "authorization",
            authorization_document,
            (
                "Status: `ATTEMPT_003_IMAGE_RECOVERY_CLOSED_NO_AUTHORITY`",
                IMAGE_RECOVERY_ID,
                IMAGE_RECOVERY_CANDIDATE_COMMIT,
                IMAGE_RECOVERY_CONSUMPTION_RECEIPT_DIGEST,
                "receipt remains durable consumption evidence",
                "Receipt deletion or mutation is not authorized",
            ),
        ),
        (
            "closure",
            closure_document,
            (
                "Status: `RECOVERY_COMPLETED_EXACT_IMAGE_REMOVAL_CLOSED`",
                IMAGE_RECOVERY_ID,
                IMAGE_RECOVERY_CANDIDATE_COMMIT,
                IMAGE_RECOVERY_CONSUMPTION_RECEIPT_DIGEST,
                "receipt remains durable consumption evidence",
                "receipt removal is not authorized",
            ),
        ),
    ):
        normalized = " ".join(document.split())
        for phrase in phrases:
            if phrase not in normalized:
                failures.append(f"O4 image recovery {label} document is missing phrase: {phrase}")


def _validate_runtime_native_repair_review(
    document: str,
    failures: list[str],
) -> None:
    normalized = " ".join(document.split())
    for phrase in (
        "Status: `GO`",
        "independent GPT-5.6 Sol xhigh read-only review",
        RUNTIME_NATIVE_REPAIR_COMMIT,
        RUNTIME_NATIVE_REPAIR_TREE,
        "changes exactly these four paths",
        RUNTIME_NATIVE_BRIDGE_DIGEST,
        RUNTIME_NATIVE_PRODUCER_DIGEST,
        "sha256:e65010ff75765b798575245d16ad28884690bac315b5f010834163754212ed2f",
        "sha256:4c39e1301aff96223cc6c02d7ae1401d11edab1e71e574b1872fc1afb73e9c7f",
        "Critical: 0",
        "High: 0",
        "Medium: 0",
        "Low: 0",
        "exact-commit disposition is `GO`",
        "runtime lineage",
        "exact inspected full image ID",
        "removes only exact bound IDs without force",
        "stable primary and cleanup failure classifications distinct",
        "24-tool/no-new-powers boundary",
        "permits preparation of a separate, exact Attempt 004 execution disposition only",
        "does not execute Attempt 004",
    ):
        if phrase not in normalized:
            failures.append(f"O4 runtime-native repair review is missing phrase: {phrase}")
    if _digest(document) != RUNTIME_NATIVE_REPAIR_REVIEW_DIGEST:
        failures.append("O4 runtime-native repair review digest is invalid")


def _validate_diagnostic_repair_review(
    document: str,
    failures: list[str],
) -> None:
    normalized = " ".join(document.split())
    for phrase in (
        "Status: `GO`",
        "independent GPT-5.6 Sol xhigh read-only review",
        DIAGNOSTIC_REPAIR_COMMIT,
        DIAGNOSTIC_REPAIR_TREE,
        "changes exactly these two paths",
        "sha256:f484e2005f16b006c2251a53af728e6c62bee812d8c3616ccd059468e6069e14",
        "sha256:ef8b455cece020d76892e6ee19775bc0099414dbbff9ff9c24aa15128702bc33",
        "Critical: 0",
        "High: 0",
        "Medium: 0",
        "Low: 0",
        "exact-commit disposition is `GO`",
        "only empty or one-newline stdout",
        "fixed Compose `ps` diagnostic",
        "bounded combined stdout/stderr",
        "no raw diagnostic output in durable evidence",
        "24-tool/no-new-powers boundary",
        "permits preparation of a separate exact Attempt 005 one-shot execution authorization only",
        "does not execute Attempt 005",
    ):
        if phrase not in normalized:
            failures.append(f"O4 diagnostic repair review is missing phrase: {phrase}")
    if _digest(document) != DIAGNOSTIC_REPAIR_REVIEW_DIGEST:
        failures.append("O4 diagnostic repair review digest is invalid")


def _validate_api_container_state_diagnostic_review(
    document: str,
    failures: list[str],
) -> None:
    normalized = " ".join(document.split())
    for phrase in (
        "Status: `GO`",
        API_CONTAINER_STATE_DIAGNOSTIC_COMMIT,
        API_CONTAINER_STATE_DIAGNOSTIC_TREE,
        API_CONTAINER_STATE_DIAGNOSTIC_PRODUCER_DIGEST,
        API_CONTAINER_STATE_DIAGNOSTIC_TEST_DIGEST,
        "Independent GPT-5.6 Sol xhigh read-only review found Critical: 0, High: 0, "
        "Medium: 0, Low: 0",
        API_CONTAINER_STATE_DIAGNOSTIC_REJECTED_001_COMMIT,
        API_CONTAINER_STATE_DIAGNOSTIC_REJECTED_001_TREE,
        "`NO_GO` with one Medium finding",
        "orphaned on interruption",
        API_CONTAINER_STATE_DIAGNOSTIC_REJECTED_002_COMMIT,
        API_CONTAINER_STATE_DIAGNOSTIC_REJECTED_002_TREE,
        "process reaping was unbounded",
        "after base-service `up` fails",
        "`service_exited_nonzero`",
        "exact Compose `ps --all --quiet ithildin-api` identity query",
        "exact validated 64-character container ID",
        "ten-second ceiling",
        "hard incremental 512-byte combined stdout-plus-stderr cap",
        "does not persist raw output, container IDs, daemon errors, logs, environment, "
        "mounts, configuration, commands, credentials, prompts, provider content, or tool results",
        "does not assign an application root cause",
        "Primary failure remains `base_services_start_failed`",
        "does not alter cleanup classification or cleanup behavior",
        "bounded repeated kill/wait/poll attempts",
        "When no earlier exception is unwinding, failure to confirm reaping raises the closed "
        "`subprocess_cleanup_unconfirmed` error",
        "During an existing unwind, bounded reap attempts complete and the original exception "
        "is preserved",
        "preparing a separate exact Attempt 006 one-shot execution authorization only",
        "does not execute Attempt 006",
        "predict that Attempt 006 will succeed",
        "new-power, new-tool",
    ):
        if phrase not in normalized:
            failures.append(f"O4 API container-state diagnostic review is missing phrase: {phrase}")
    if _digest(document) != API_CONTAINER_STATE_DIAGNOSTIC_REVIEW_DIGEST:
        failures.append("O4 API container-state diagnostic review digest is invalid")


def _validate_application_startup_stage_diagnostic_review(
    document: str,
    failures: list[str],
) -> None:
    normalized = " ".join(document.split())
    for phrase in (
        "Status: `GO`",
        APPLICATION_STARTUP_STAGE_DIAGNOSTIC_COMMIT,
        APPLICATION_STARTUP_STAGE_DIAGNOSTIC_TREE,
        "Independent GPT-5.6 Sol xhigh read-only review found Critical: 0, High: 0, "
        "Medium: 0, Low: 0",
        "these 12 closed startup stages",
        "`launcher_entered`",
        "`shutdown_complete`",
        "canonical ASCII JSON",
        "owner-matching `0700` no-follow directory",
        "exclusive `0600` temporary file",
        "service diagnostic classifies the API as `service_exited_nonzero`",
        "`api_application_exit_nonzero_no_engine_error`",
        "limited to 256 bytes",
        "only `collection_status`, `collection_reason_code`, and normalized `last_emitted_stage`",
        "does not scrape or persist logs",
        "does not establish a root cause",
        "389 focused tests",
        "strict mypy",
        "no-new-powers gate",
        "exact 24-tool invariant",
        "agent-workflow check",
        "preparation of a separate exact Attempt 007 one-shot execution authorization only",
        "does not execute Attempt 007",
    ):
        if phrase not in normalized:
            failures.append(
                f"O4 application startup-stage diagnostic review is missing phrase: {phrase}"
            )
    for path, digest in APPLICATION_STARTUP_STAGE_PATH_DIGESTS.items():
        stage_digest = cast(str, digest)
        if path not in normalized or stage_digest not in normalized:
            failures.append(f"O4 application startup-stage review path binding is missing: {path}")
    if _digest(document) != APPLICATION_STARTUP_STAGE_DIAGNOSTIC_REVIEW_DIGEST:
        failures.append("O4 application startup-stage diagnostic review digest is invalid")


def _validate_image_readability_repair_review(
    document: str,
    failures: list[str],
) -> None:
    normalized = " ".join(document.split())
    for phrase in (
        "Status: `GO`",
        IMAGE_READABILITY_REPAIR_COMMIT,
        IMAGE_READABILITY_REPAIR_TREE,
        "Critical: 0",
        "High: 0",
        "Medium: 0",
        "Low: 0",
        "exact-commit disposition is `GO`",
        "runtime readability and traversal only",
        "`a+rX`, which cannot add write permission",
        "Hermes scratch directory alone",
        "exact non-root identities `10001:10001` and `10002:10002`",
        "exact non-root identity `10000:10000`",
        "valid unary `test -x`, `test -r`, or the single bounded Hermes scratch `test -w`",
        "exactly one operand",
        "changes no Compose file",
        "runtime snapshot behavior",
        "exact 24-tool invariant",
        "no-new-powers gate",
        "190 focused tests",
        "strict mypy",
        "agent-workflow check",
        "separate exact Attempt 008 one-shot execution authorization only",
        "does not execute Attempt 008",
    ):
        if phrase not in normalized:
            failures.append(f"O4 image-readability repair review is missing phrase: {phrase}")
    for path, digest in IMAGE_READABILITY_REPAIR_PATH_DIGESTS.items():
        path_digest = cast(str, digest)
        if path not in normalized or path_digest not in normalized:
            failures.append(f"O4 image-readability review path binding is missing: {path}")
    if _digest(document) != IMAGE_READABILITY_REPAIR_REVIEW_DIGEST:
        failures.append("O4 image-readability repair review digest is invalid")


def _validate_enrollment_output_projection_repair_review(
    document: str,
    failures: list[str],
) -> None:
    normalized = " ".join(document.split())
    for phrase in (
        "Status: `GO`",
        ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REJECTED_COMMIT,
        ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REJECTED_TREE,
        "one Medium finding (`M1`)",
        "not authorized for execution",
        ENROLLMENT_OUTPUT_PROJECTION_REPAIR_COMMIT,
        ENROLLMENT_OUTPUT_PROJECTION_REPAIR_TREE,
        ENROLLMENT_OUTPUT_PROJECTION_REPAIR_BASE_COMMIT,
        "Critical: 0",
        "High: 0",
        "Medium: 0",
        "Low: 0",
        "exact-commit disposition is `GO`",
        "captures subprocess input and output as bytes",
        "strict UTF-8",
        "closed canonical projection containing exactly three string fields",
        "`node_id`, `principal_id`, and `workspace_id`",
        "`principal_id` must equal `agent:node.{node_id}`",
        "`private_key_present`",
        "does not execute Attempt 009",
        "separate exact Attempt 009 one-shot execution authorization only",
        "new isolated attempt",
        "not a retry, cleanup, revocation, or reconciliation of Attempt 008",
        "preflight must fail closed before live work",
        "do not prove that the retained Attempt 008 enrollment was absent or revoked",
        "does not revoke or reconcile the ambiguous Attempt 008 enrollment",
        "governed tool or power",
        "release, promotion, production, credential custody, or UAT",
    ):
        if phrase not in normalized:
            failures.append(
                f"O4 enrollment-output projection repair review is missing phrase: {phrase}"
            )
    for path, digest in ENROLLMENT_OUTPUT_PROJECTION_REPAIR_PATH_DIGESTS.items():
        path_digest = cast(str, digest)
        if path not in normalized or path_digest not in normalized:
            failures.append(
                f"O4 enrollment-output projection repair path binding is missing: {path}"
            )
    for forbidden in ("`agent_id`", "`gateway`", "`registered`", "five-field"):
        if forbidden in normalized:
            failures.append(
                "O4 enrollment-output projection repair review contains stale projection "
                f"vocabulary: {forbidden}"
            )
    if _digest(document) != ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REVIEW_DIGEST:
        failures.append("O4 enrollment-output projection repair review digest is invalid")


def _validate_attempt_008_disposition(
    disposition: JsonObject,
    document: str,
    failures: list[str],
) -> None:
    expected = {
        "record_status": (
            "ATTEMPT_008_CONSUMED_ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REQUIRED_"
            "RECOVERY_REQUIRED_NO_LIVE_AUTHORITY"
        ),
        "attempt_id": ATTEMPT_008_ID,
        "attempted_candidate_commit": ATTEMPT_008_CANDIDATE_COMMIT,
        "attempted_candidate_tree": ATTEMPT_008_CANDIDATE_TREE,
        "run_id": ATTEMPT_008_RUN_ID,
        "compose_project": ATTEMPT_008_PROJECT,
        "outward_failure_code": "recovery_required",
        "next_action": (
            "prepare_separately_reviewed_enrollment_output_projection_repair_"
            "without_retry_or_raw_stdout_claim"
        ),
    }
    for key, value in expected.items():
        if disposition.get(key) != value:
            failures.append(f"O4 Attempt 008 disposition {key} is not exact")
    if disposition.get("diagnostic_facts") != {
        "base_build_completed": True,
        "bridge_build_completed": True,
        "bound_image_identity_count": 4,
        "highest_completed_stage": 7,
        "primary_failure_code": "subprocess_output_rejected",
        "cleanup_failure_codes": ["enrollment_outcome_ambiguous"],
        "outward_failure_code": "recovery_required",
        "diagnostic_recovery_required": True,
    }:
        failures.append("O4 Attempt 008 diagnostic facts are not exact")
    if disposition.get("candidate_code_analysis") != {
        "classification": "deterministic_candidate_code_path_incompatibility",
        "evidence_basis": "exact_candidate_source_plus_stage_and_return_path_evidence",
        "node_cli_safe_summary_field": "private_key_present",
        "producer_forbidden_output_pattern": "private[_ -]?key",
        "producer_validation_order": (
            "lexical_forbidden_output_scan_precedes_json_projection_validation"
        ),
        "candidate_defect_identified": True,
        "retained_raw_stdout_proof_claimed": False,
        "raw_stdout_inspected_for_this_disposition": False,
    }:
        failures.append("O4 Attempt 008 candidate code analysis is not exact")
    if disposition.get("recovery_posture") != {
        "cleanup_succeeded_claimed": False,
        "exact_image_absence_claimed": False,
        "run_image_reference_absence_claimed": False,
        "container_absence_claimed": False,
        "volume_absence_claimed": False,
        "network_absence_claimed": False,
        "general_docker_absence_claimed": False,
        "runtime_plaintext_absence_claimed": False,
        "reconciliation_required": True,
        "recovery_authorized": False,
        "evidence_deletion_authorized": False,
    }:
        failures.append("O4 Attempt 008 recovery claim limits are not exact")
    receipt = disposition.get("retained_receipt")
    if not isinstance(receipt, dict) or any(
        receipt.get(key) != value
        for key, value in {
            "receipt_root": f"{ATTEMPT_002_RECEIPT_BASE.as_posix()}/{ATTEMPT_008_RUN_ID}",
            "receipt_root_mode": "0700",
            "disposition_size_bytes": 119,
            "disposition_sha256": ATTEMPT_008_DISPOSITION_RECEIPT_DIGEST,
            "diagnostic_size_bytes": ATTEMPT_008_DIAGNOSTIC_SIZE,
            "diagnostic_sha256": ATTEMPT_008_DIAGNOSTIC_RECEIPT_DIGEST,
            "candidate_manifest_size_bytes": ATTEMPT_008_MANIFEST_SIZE,
            "candidate_manifest_sha256": ATTEMPT_008_MANIFEST_RECEIPT_DIGEST,
            "candidate_snapshot_file_count": ATTEMPT_008_SNAPSHOT_FILE_COUNT,
            "published_report_success_claimed": False,
        }.items()
    ):
        failures.append("O4 Attempt 008 retained receipt is not exact")
    if disposition.get("tracked_closure_scope") != ATTEMPT_008_CLOSURE_CONTROL_PATH_ALLOWLIST:
        failures.append("O4 Attempt 008 closure scope is not exact")
    if disposition.get("attempt_contract") != {
        "attempt_consumed": True,
        "execution_attempt_budget": 0,
        "retry_authorized": False,
        "automatic_retry_authorized": False,
        "post_failure_execution_authorized": False,
        "recovery_required": True,
        "recovery_authorized": False,
        "evidence_deletion_authorized": False,
    }:
        failures.append("O4 Attempt 008 contract is not closed")
    if not _exact_json_equal(disposition.get("authority"), CLOSED_AUTHORITY):
        failures.append("O4 Attempt 008 disposition authority is not closed")
    normalized = " ".join(document.split())
    for phrase in (
        ATTEMPT_008_CANDIDATE_COMMIT,
        ATTEMPT_008_CANDIDATE_TREE,
        ATTEMPT_008_RUN_ID,
        ATTEMPT_008_PROJECT,
        "`subprocess_output_rejected`",
        "`[enrollment_outcome_ambiguous]`",
        "deterministic code-path incompatibility",
        "`private_key_present`",
        "`private[_ -]?key`",
        "before the enrollment JSON projection is parsed and validated",
        "not retained raw stdout proof",
        "raw stdout was not inspected",
        "Cleanup success is not claimed",
        "No image ID, run image reference, container, volume, network, runtime plaintext, "
        "or general Docker absence is claimed",
        ATTEMPT_008_DISPOSITION_RECEIPT_DIGEST,
        ATTEMPT_008_DIAGNOSTIC_RECEIPT_DIGEST,
        ATTEMPT_008_MANIFEST_RECEIPT_DIGEST,
        "all 19 authority fields are false",
        "separately reviewed enrollment-output projection repair",
        "does not authorize retry",
    ):
        if phrase not in normalized:
            failures.append(f"O4 Attempt 008 disposition doc is missing phrase: {phrase}")
    if _digest(document) != ATTEMPT_008_DISPOSITION_DOCUMENT_DIGEST:
        failures.append("O4 Attempt 008 disposition document digest is invalid")


def _validate_attempt_004_disposition(
    disposition: JsonObject,
    document: str,
    failures: list[str],
) -> None:
    expected_scalars = {
        "schema_version": "1",
        "record_type": "local_v1_lv1_003_o4_attempt_disposition",
        "record_status": "ATTEMPT_004_CONSUMED_REPAIR_REQUIRED_NO_LIVE_AUTHORITY",
        "ticket_id": "LV1-003",
        "outcome_id": "O4",
        "attempt_id": ATTEMPT_004_ID,
        "attempted_candidate_commit": ATTEMPT_004_CANDIDATE_COMMIT,
        "attempted_candidate_tree": ATTEMPT_004_CANDIDATE_TREE,
        "operator_command": ATTEMPT_002_OPERATOR_COMMAND,
        "module_command": PRODUCER_MODULE_INVOCATION,
        "run_id": ATTEMPT_004_RUN_ID,
        "compose_project": ATTEMPT_004_PROJECT,
        "outward_failure_code": "recovery_required",
        "next_action": (
            "prepare_separate_reviewed_not_found_normalization_and_bounded_"
            "base_service_start_diagnostic_repair"
        ),
    }
    for key, expected in expected_scalars.items():
        if not _exact_json_equal(disposition.get(key), expected):
            failures.append(f"O4 Attempt 004 disposition {key} is not exact")
    diagnostic = disposition.get("diagnostic_facts")
    if not isinstance(diagnostic, dict) or not _exact_json_equal(
        {
            "base_build_completed": diagnostic.get("base_build_completed"),
            "bridge_build_completed": diagnostic.get("bridge_build_completed"),
            "bound_image_identity_count": diagnostic.get("bound_image_identity_count"),
            "highest_completed_stage": diagnostic.get("highest_completed_stage"),
            "primary_failure_code": diagnostic.get("primary_failure_code"),
            "cleanup_failure_codes": diagnostic.get("cleanup_failure_codes"),
            "outward_failure_code": diagnostic.get("outward_failure_code"),
            "diagnostic_recovery_required": diagnostic.get("diagnostic_recovery_required"),
        },
        {
            "base_build_completed": True,
            "bridge_build_completed": True,
            "bound_image_identity_count": 4,
            "highest_completed_stage": 7,
            "primary_failure_code": "base_services_start_failed",
            "cleanup_failure_codes": ["owned_image_id_absence_probe_failed"],
            "outward_failure_code": "recovery_required",
            "diagnostic_recovery_required": True,
        },
    ):
        failures.append("O4 Attempt 004 disposition diagnostic facts are not exact")
    classifier = disposition.get("verified_classifier_mismatch")
    if not isinstance(classifier, dict) or not _exact_json_equal(
        classifier,
        {
            "classification": "docker_absent_image_id_stdout_normalization_mismatch",
            "docker_absent_id_response_included_stdout_newline": True,
            "producer_required_empty_stdout": True,
            "cleanup_failure_code": "owned_image_id_absence_probe_failed",
            "producer_repair_included": False,
            "generic_docker_absence_claimed": False,
            "cleanup_completed_claimed": False,
        },
    ):
        failures.append("O4 Attempt 004 classifier mismatch record is not exact")
    observation = disposition.get("point_in_time_post_attempt_observation")
    if not isinstance(observation, dict) or not _exact_json_equal(
        observation,
        {
            "observation_scope": "exact_run_scoped_read_only_post_failure",
            "all_four_run_references_absent": True,
            "all_four_exact_image_ids_absent": True,
            "exact_project_label_containers": 0,
            "exact_project_label_volumes": 0,
            "exact_project_label_networks": 0,
            "runtime_run_directory_absent": True,
            "runtime_base_entries": [IMAGE_RECOVERY_CONSUMPTION_RECEIPT_NAME],
            "ongoing_live_truth_claimed": False,
            "general_docker_absence_claimed": False,
            "cleanup_completed_claimed": False,
        },
    ):
        failures.append("O4 Attempt 004 point-in-time observation is not exact")
    attempt_contract = disposition.get("attempt_contract")
    if not isinstance(attempt_contract, dict) or not _exact_json_equal(
        attempt_contract,
        {
            "attempt_consumed": True,
            "execution_attempt_budget": 0,
            "retry_authorized": False,
            "automatic_retry_authorized": False,
            "post_failure_execution_authorized": False,
            "image_recovery_required": False,
            "image_recovery_authorized": False,
            "evidence_deletion_authorized": False,
            "separate_reviewed_producer_repair_required": True,
            "separate_new_attempt_disposition_required": True,
        },
    ):
        failures.append("O4 Attempt 004 disposition attempt contract is not exact")
    if not _exact_json_equal(
        disposition.get("tracked_closure_scope"),
        ATTEMPT_004_CLOSURE_CONTROL_PATH_ALLOWLIST,
    ):
        failures.append("O4 Attempt 004 tracked closure scope is not exact")
    if not _exact_json_equal(disposition.get("authority"), CLOSED_AUTHORITY):
        failures.append("O4 Attempt 004 disposition authority is not closed")
    normalized = " ".join(document.split())
    for phrase in (
        "Status: `ATTEMPT_004_CONSUMED_REPAIR_REQUIRED_NO_LIVE_AUTHORITY`",
        ATTEMPT_004_ID,
        ATTEMPT_004_CANDIDATE_COMMIT,
        ATTEMPT_004_CANDIDATE_TREE,
        ATTEMPT_004_RUN_ID,
        ATTEMPT_004_PROJECT,
        "base_services_start_failed",
        "owned_image_id_absence_probe_failed",
        "outward result was `recovery_required`",
        "verified classifier mismatch",
        "stdout newline",
        "separate read-only postcheck",
        "does not establish generic Docker absence",
        "no image recovery is required or authorized",
        ATTEMPT_004_DISPOSITION_RECEIPT_DIGEST,
        ATTEMPT_004_DIAGNOSTIC_RECEIPT_DIGEST,
        ATTEMPT_004_MANIFEST_RECEIPT_DIGEST,
        "exactly 664 files",
        "exactly these eight paths",
        "all 19 authority fields are false",
        "No producer repair is included",
        "separate reviewed producer repair",
    ):
        if phrase not in normalized:
            failures.append(f"O4 Attempt 004 disposition doc is missing phrase: {phrase}")
    if _digest(document) != ATTEMPT_004_DISPOSITION_DOCUMENT_DIGEST:
        failures.append("O4 Attempt 004 disposition document digest is invalid")


def _validate_attempt_005_disposition(
    disposition: JsonObject,
    document: str,
    failures: list[str],
) -> None:
    expected_fields = {
        "schema_version",
        "record_type",
        "record_status",
        "ticket_id",
        "outcome_id",
        "attempt_id",
        "attempted_candidate_commit",
        "attempted_candidate_tree",
        "operator_command",
        "module_command",
        "run_id",
        "compose_project",
        "outward_failure_code",
        "diagnostic_facts",
        "in_run_cleanup_result",
        "point_in_time_post_attempt_observation",
        "retained_receipt",
        "runtime_posture",
        "tracked_closure_scope",
        "attempt_contract",
        "next_action",
        "authority",
    }
    if set(disposition) != expected_fields:
        failures.append("O4 Attempt 005 disposition fields are not closed")
    expected_scalars = {
        "schema_version": "1",
        "record_type": "local_v1_lv1_003_o4_attempt_disposition",
        "record_status": ("ATTEMPT_005_CONSUMED_API_EXIT_DIAGNOSTIC_REQUIRED_NO_LIVE_AUTHORITY"),
        "ticket_id": "LV1-003",
        "outcome_id": "O4",
        "attempt_id": ATTEMPT_005_ID,
        "attempted_candidate_commit": ATTEMPT_005_CANDIDATE_COMMIT,
        "attempted_candidate_tree": ATTEMPT_005_CANDIDATE_TREE,
        "operator_command": ATTEMPT_002_OPERATOR_COMMAND,
        "module_command": PRODUCER_MODULE_INVOCATION,
        "run_id": ATTEMPT_005_RUN_ID,
        "compose_project": ATTEMPT_005_PROJECT,
        "outward_failure_code": "base_services_start_failed",
        "next_action": (
            "prepare_separate_reviewed_api_exit_diagnostic_repair_without_assigning_cause"
        ),
    }
    for key, expected in expected_scalars.items():
        if not _exact_json_equal(disposition.get(key), expected):
            failures.append(f"O4 Attempt 005 disposition {key} is not exact")
    expected_identities = [
        {
            "service": "ithildin-api",
            "reference": "ithildin/api-o4:b806c1bd",
            "image_id": ("sha256:e4ca0c62c670f38f150bb09f42a356e0d5b2956cf7cb56a3bd729004a1ffcb33"),
        },
        {
            "service": "ithildin-ui",
            "reference": "ithildin/ui-o4:b806c1bd",
            "image_id": ("sha256:a1e78335549b50210d6f607dc0335e0263d60fc2d9ff5e4e9ac6a303af3b9b38"),
        },
        {
            "service": "ithildin-node",
            "reference": "ithildin/node-o4:b806c1bd",
            "image_id": ("sha256:a876ac0a41cd64e57c5b6f28839363d831187323733280929a74ffe27a0e8294"),
        },
        {
            "service": "hermes",
            "reference": "ithildin/hermes-node-bridge-o4:b806c1bd",
            "image_id": ("sha256:702bd8613619440585ff6f2011c2e49fb07aed587223eab9d2298604e775ebf9"),
        },
    ]
    if not _exact_json_equal(
        disposition.get("diagnostic_facts"),
        {
            "base_build_completed": True,
            "bridge_build_completed": True,
            "bound_image_identity_count": 4,
            "bound_image_identities": expected_identities,
            "highest_completed_stage": 7,
            "primary_failure_code": "base_services_start_failed",
            "cleanup_failure_codes": [],
            "outward_failure_code": "base_services_start_failed",
            "diagnostic_recovery_required": False,
            "base_service_start_diagnostic": {
                "collection_status": "complete",
                "reason_code": "base_service_start_state_collected",
                "services": {
                    "ithildin-api": "service_exited_nonzero",
                    "ithildin-ui": "service_created",
                },
            },
        },
    ):
        failures.append("O4 Attempt 005 disposition diagnostic facts are not exact")
    if not _exact_json_equal(
        disposition.get("in_run_cleanup_result"),
        {
            "cleanup_succeeded": True,
            "evidence_source": "reviewed_bounded_diagnostic",
            "cleanup_failure_codes": [],
            "recovery_required": False,
            "scope": "exact_bound_attempt_005_resources",
            "generic_docker_absence_claimed": False,
            "ongoing_live_truth_claimed": False,
        },
    ):
        failures.append("O4 Attempt 005 in-run cleanup result is not exact")
    if not _exact_json_equal(
        disposition.get("point_in_time_post_attempt_observation"),
        {
            "observation_scope": "exact_run_scoped_read_only_post_failure",
            "all_four_run_references_absent": True,
            "all_four_exact_image_ids_absent": True,
            "exact_project_label_containers": 0,
            "exact_project_label_volumes": 0,
            "exact_project_label_networks": 0,
            "runtime_run_directory_absent": True,
            "runtime_plaintext_absent": True,
            "runtime_base_entries": [IMAGE_RECOVERY_CONSUMPTION_RECEIPT_NAME],
            "ongoing_live_truth_claimed": False,
            "general_docker_absence_claimed": False,
        },
    ):
        failures.append("O4 Attempt 005 point-in-time observation is not exact")
    receipt_root = f"{ATTEMPT_002_RECEIPT_BASE.as_posix()}/{ATTEMPT_005_RUN_ID}"
    if not _exact_json_equal(
        disposition.get("retained_receipt"),
        {
            "receipt_root": receipt_root,
            "receipt_root_mode": "0700",
            "receipt_entries": [
                "candidate",
                "candidate-manifest.json",
                "diagnostic.json",
                "disposition.json",
            ],
            "disposition_path": f"{receipt_root}/disposition.json",
            "disposition_mode": "0600",
            "disposition_size_bytes": len(ATTEMPT_005_DISPOSITION_BYTES),
            "disposition_sha256": ATTEMPT_005_DISPOSITION_RECEIPT_DIGEST,
            "diagnostic_path": f"{receipt_root}/diagnostic.json",
            "diagnostic_mode": "0600",
            "diagnostic_size_bytes": ATTEMPT_005_DIAGNOSTIC_SIZE,
            "diagnostic_sha256": ATTEMPT_005_DIAGNOSTIC_RECEIPT_DIGEST,
            "candidate_manifest_path": f"{receipt_root}/candidate-manifest.json",
            "candidate_manifest_mode": "0600",
            "candidate_manifest_size_bytes": ATTEMPT_005_MANIFEST_SIZE,
            "candidate_manifest_sha256": ATTEMPT_005_MANIFEST_RECEIPT_DIGEST,
            "candidate_snapshot_path": f"{receipt_root}/candidate",
            "candidate_snapshot_mode": "0500",
            "candidate_snapshot_file_count": ATTEMPT_005_SNAPSHOT_FILE_COUNT,
            "published_report_base_exists": False,
        },
    ):
        failures.append("O4 Attempt 005 retained receipt record is not exact")
    if not _exact_json_equal(
        disposition.get("runtime_posture"),
        {
            "run_directory_exists": False,
            "runtime_plaintext_exists": False,
            "runtime_base_exists": True,
            "runtime_base_mode": "0700",
            "runtime_base_entries": [IMAGE_RECOVERY_CONSUMPTION_RECEIPT_NAME],
            "recovery_consumption_receipt_mode": "0600",
            "recovery_consumption_receipt_size_bytes": len(
                IMAGE_RECOVERY_CONSUMPTION_RECEIPT_BYTES
            ),
            "recovery_consumption_receipt_sha256": (IMAGE_RECOVERY_CONSUMPTION_RECEIPT_DIGEST),
        },
    ):
        failures.append("O4 Attempt 005 runtime posture is not exact")
    if not _exact_json_equal(
        disposition.get("attempt_contract"),
        {
            "attempt_consumed": True,
            "execution_attempt_budget": 0,
            "retry_authorized": False,
            "automatic_retry_authorized": False,
            "post_failure_execution_authorized": False,
            "image_recovery_required": False,
            "image_recovery_authorized": False,
            "evidence_deletion_authorized": False,
            "separate_reviewed_producer_repair_required": True,
            "separate_new_attempt_disposition_required": True,
        },
    ):
        failures.append("O4 Attempt 005 disposition attempt contract is not exact")
    if not _exact_json_equal(
        disposition.get("tracked_closure_scope"),
        ATTEMPT_005_CLOSURE_CONTROL_PATH_ALLOWLIST,
    ):
        failures.append("O4 Attempt 005 tracked closure scope is not exact")
    if not _exact_json_equal(disposition.get("authority"), CLOSED_AUTHORITY):
        failures.append("O4 Attempt 005 disposition authority is not closed")
    normalized = " ".join(document.split())
    for phrase in (
        "Status: `ATTEMPT_005_CONSUMED_API_EXIT_DIAGNOSTIC_REQUIRED_NO_LIVE_AUTHORITY`",
        ATTEMPT_005_ID,
        ATTEMPT_005_CANDIDATE_COMMIT,
        ATTEMPT_005_CANDIDATE_TREE,
        ATTEMPT_005_RUN_ID,
        ATTEMPT_005_PROJECT,
        "primary and outward failure code was `base_services_start_failed`",
        "`ithildin-api` as `service_exited_nonzero`",
        "`ithildin-ui` as `service_created`",
        "do not state why the API exited",
        "`cleanup_failure_codes` is empty",
        "`recovery_required` is false",
        "successful in-run cleanup for the exact bound Attempt 005 resources",
        "separate read-only, exact-run-scoped postcheck",
        "not ongoing live truth",
        "no image recovery is required or authorized",
        ATTEMPT_005_DISPOSITION_RECEIPT_DIGEST,
        ATTEMPT_005_DIAGNOSTIC_RECEIPT_DIGEST,
        ATTEMPT_005_MANIFEST_RECEIPT_DIGEST,
        "exactly 664 files",
        "Attempts 002 through 005 retained receipts",
        "sole runtime-base entry",
        "exactly these eight paths",
        "all 19 authority fields are false",
        "separate reviewed API-exit diagnostic repair",
        "assigns no cause",
    ):
        if phrase not in normalized:
            failures.append(f"O4 Attempt 005 disposition doc is missing phrase: {phrase}")
    if _digest(document) != ATTEMPT_005_DISPOSITION_DOCUMENT_DIGEST:
        failures.append("O4 Attempt 005 disposition document digest is invalid")


def _validate_attempt_006_disposition(
    disposition: JsonObject,
    document: str,
    failures: list[str],
) -> None:
    expected_fields = {
        "schema_version",
        "record_type",
        "record_status",
        "ticket_id",
        "outcome_id",
        "attempt_id",
        "attempted_candidate_commit",
        "attempted_candidate_tree",
        "operator_command",
        "module_command",
        "run_id",
        "compose_project",
        "outward_failure_code",
        "diagnostic_facts",
        "in_run_cleanup_result",
        "point_in_time_post_attempt_observation",
        "retained_receipt",
        "runtime_posture",
        "tracked_closure_scope",
        "attempt_contract",
        "next_action",
        "authority",
    }
    if set(disposition) != expected_fields:
        failures.append("O4 Attempt 006 disposition fields are not closed")
    expected_scalars = {
        "schema_version": "1",
        "record_type": "local_v1_lv1_003_o4_attempt_disposition",
        "record_status": (
            "ATTEMPT_006_CONSUMED_APPLICATION_STARTUP_DIAGNOSTIC_REQUIRED_NO_LIVE_AUTHORITY"
        ),
        "ticket_id": "LV1-003",
        "outcome_id": "O4",
        "attempt_id": ATTEMPT_006_ID,
        "attempted_candidate_commit": ATTEMPT_006_CANDIDATE_COMMIT,
        "attempted_candidate_tree": ATTEMPT_006_CANDIDATE_TREE,
        "operator_command": ATTEMPT_002_OPERATOR_COMMAND,
        "module_command": PRODUCER_MODULE_INVOCATION,
        "run_id": ATTEMPT_006_RUN_ID,
        "compose_project": ATTEMPT_006_PROJECT,
        "outward_failure_code": "base_services_start_failed",
        "next_action": (
            "prepare_separately_reviewed_application_emitted_closed_startup_stage_"
            "diagnostic_without_log_scraping_or_root_cause_guess"
        ),
    }
    for key, value in expected_scalars.items():
        if not _exact_json_equal(disposition.get(key), value):
            failures.append(f"O4 Attempt 006 disposition {key} is not exact")
    diagnostic = disposition.get("diagnostic_facts")
    if not isinstance(diagnostic, dict):
        failures.append("O4 Attempt 006 diagnostic facts are unavailable")
    else:
        expected_diagnostic_scalars = {
            "base_build_completed": True,
            "bridge_build_completed": True,
            "bound_image_identity_count": 4,
            "highest_completed_stage": 7,
            "primary_failure_code": "base_services_start_failed",
            "cleanup_failure_codes": [],
            "outward_failure_code": "base_services_start_failed",
            "diagnostic_recovery_required": False,
            "oom_killed": False,
            "container_engine_error_present": False,
            "application_root_cause_known": False,
        }
        for diagnostic_key, diagnostic_value in expected_diagnostic_scalars.items():
            if not _exact_json_equal(
                diagnostic.get(diagnostic_key),
                diagnostic_value,
            ):
                failures.append(f"O4 Attempt 006 diagnostic {diagnostic_key} is not exact")
        identities = diagnostic.get("bound_image_identities")
        expected_identity_triples = [
            (
                "ithildin-api",
                "ithildin/api-o4:b00570b3",
                "sha256:e75264be1cf08effff08d122324410435955dd6c816c506f1b1d5da5614527a5",
            ),
            (
                "ithildin-ui",
                "ithildin/ui-o4:b00570b3",
                "sha256:2d97d8658498978da4ca610dbd51e0b6aa55bf9b35f0815a002b65054a208ce5",
            ),
            (
                "ithildin-node",
                "ithildin/node-o4:b00570b3",
                "sha256:1ae93646eca07cf3472ea70952ee83083228eb1924aebf91ab6fa0cd54cb0ebb",
            ),
            (
                "hermes",
                "ithildin/hermes-node-bridge-o4:b00570b3",
                "sha256:1a1eb3d53d106428f1266e8ce1d1799fd6b6074449673767a2a2016da647794f",
            ),
        ]
        if (
            not isinstance(identities, list)
            or [
                (item.get("service"), item.get("reference"), item.get("image_id"))
                for item in identities
                if isinstance(item, dict)
            ]
            != expected_identity_triples
        ):
            failures.append("O4 Attempt 006 bound image identities are not exact")
        if not _exact_json_equal(
            diagnostic.get("base_service_start_diagnostic"),
            {
                "collection_status": "complete",
                "reason_code": "base_service_start_state_collected",
                "services": {
                    "ithildin-api": "service_exited_nonzero",
                    "ithildin-ui": "service_created",
                },
                "api_container_state_diagnostic": {
                    "collection_status": "complete",
                    "collection_reason_code": "api_container_state_collected",
                    "cause_code": "api_application_exit_nonzero_no_engine_error",
                    "health_status": "unhealthy",
                },
            },
        ):
            failures.append("O4 Attempt 006 startup diagnostics are not exact")
    cleanup = disposition.get("in_run_cleanup_result")
    if not isinstance(cleanup, dict) or (
        cleanup.get("cleanup_succeeded") is not True
        or cleanup.get("cleanup_failure_codes") != []
        or cleanup.get("recovery_required") is not False
        or cleanup.get("scope") != "exact_bound_attempt_006_resources"
        or cleanup.get("generic_docker_absence_claimed") is not False
        or cleanup.get("ongoing_live_truth_claimed") is not False
    ):
        failures.append("O4 Attempt 006 cleanup result is not exact")
    observation = disposition.get("point_in_time_post_attempt_observation")
    if not isinstance(observation, dict) or any(
        observation.get(key) != value
        for key, value in {
            "all_four_run_references_absent": True,
            "all_four_exact_image_ids_absent": True,
            "exact_project_label_containers": 0,
            "exact_project_label_volumes": 0,
            "exact_project_label_networks": 0,
            "temporary_docker_config_cleaned": True,
            "runtime_run_directory_absent": True,
            "runtime_plaintext_absent": True,
            "ongoing_live_truth_claimed": False,
            "general_docker_absence_claimed": False,
        }.items()
    ):
        failures.append("O4 Attempt 006 point-in-time observation is not exact")
    receipt = disposition.get("retained_receipt")
    receipt_root = f"{ATTEMPT_002_RECEIPT_BASE.as_posix()}/{ATTEMPT_006_RUN_ID}"
    if not isinstance(receipt, dict) or any(
        receipt.get(key) != value
        for key, value in {
            "receipt_root": receipt_root,
            "disposition_size_bytes": 128,
            "disposition_sha256": ATTEMPT_006_DISPOSITION_RECEIPT_DIGEST,
            "diagnostic_size_bytes": ATTEMPT_006_DIAGNOSTIC_SIZE,
            "diagnostic_sha256": ATTEMPT_006_DIAGNOSTIC_RECEIPT_DIGEST,
            "candidate_manifest_size_bytes": ATTEMPT_006_MANIFEST_SIZE,
            "candidate_manifest_sha256": ATTEMPT_006_MANIFEST_RECEIPT_DIGEST,
            "candidate_snapshot_file_count": ATTEMPT_006_SNAPSHOT_FILE_COUNT,
            "published_report_base_exists": False,
        }.items()
    ):
        failures.append("O4 Attempt 006 retained receipt is not exact")
    if disposition.get("tracked_closure_scope") != ATTEMPT_006_CLOSURE_CONTROL_PATH_ALLOWLIST:
        failures.append("O4 Attempt 006 tracked closure scope is not exact")
    attempt_contract = disposition.get("attempt_contract")
    if not isinstance(attempt_contract, dict) or any(
        attempt_contract.get(key) != value
        for key, value in {
            "attempt_consumed": True,
            "execution_attempt_budget": 0,
            "retry_authorized": False,
            "automatic_retry_authorized": False,
            "post_failure_execution_authorized": False,
            "image_recovery_required": False,
            "image_recovery_authorized": False,
            "evidence_deletion_authorized": False,
        }.items()
    ):
        failures.append("O4 Attempt 006 attempt contract is not closed")
    if not _exact_json_equal(disposition.get("authority"), CLOSED_AUTHORITY):
        failures.append("O4 Attempt 006 disposition authority is not closed")
    normalized = " ".join(document.split())
    for phrase in (
        "Status: `ATTEMPT_006_CONSUMED_APPLICATION_STARTUP_DIAGNOSTIC_REQUIRED_NO_LIVE_AUTHORITY`",
        ATTEMPT_006_ID,
        ATTEMPT_006_CANDIDATE_COMMIT,
        ATTEMPT_006_CANDIDATE_TREE,
        ATTEMPT_006_RUN_ID,
        ATTEMPT_006_PROJECT,
        "`api_application_exit_nonzero_no_engine_error`",
        "health `unhealthy`",
        "exact application root cause remains unknown",
        "temporary Docker configuration cleaned",
        ATTEMPT_006_DISPOSITION_RECEIPT_DIGEST,
        ATTEMPT_006_DIAGNOSTIC_RECEIPT_DIGEST,
        ATTEMPT_006_MANIFEST_RECEIPT_DIGEST,
        "Attempts 002 through 006 retained receipts",
        "exactly these eight paths",
        "all 19 authority fields are false",
        "separately reviewed application-emitted closed startup-stage diagnostic",
        "must not scrape logs",
        "does not guess the application root cause",
    ):
        if phrase not in normalized:
            failures.append(f"O4 Attempt 006 disposition doc is missing phrase: {phrase}")
    if _digest(document) != ATTEMPT_006_DISPOSITION_DOCUMENT_DIGEST:
        failures.append("O4 Attempt 006 disposition document digest is invalid")


def _validate_attempt_007_disposition(
    disposition: JsonObject,
    document: str,
    failures: list[str],
) -> None:
    expected = {
        "record_status": (
            "ATTEMPT_007_CONSUMED_PRELAUNCH_IMAGE_READABILITY_"
            "INVESTIGATION_REQUIRED_NO_LIVE_AUTHORITY"
        ),
        "attempt_id": ATTEMPT_007_ID,
        "attempted_candidate_commit": ATTEMPT_007_CANDIDATE_COMMIT,
        "attempted_candidate_tree": ATTEMPT_007_CANDIDATE_TREE,
        "run_id": ATTEMPT_007_RUN_ID,
        "compose_project": ATTEMPT_007_PROJECT,
        "outward_failure_code": "base_services_start_failed",
        "next_action": (
            "prepare_separately_reviewed_prelaunch_docker_image_readability_"
            "repair_investigation_without_log_scraping_or_root_cause_claim"
        ),
    }
    for key, value in expected.items():
        if disposition.get(key) != value:
            failures.append(f"O4 Attempt 007 disposition {key} is not exact")
    diagnostic = disposition.get("diagnostic_facts")
    if not isinstance(diagnostic, dict) or diagnostic.get("base_service_start_diagnostic") != {
        "collection_status": "complete",
        "reason_code": "base_service_start_state_collected",
        "services": {
            "ithildin-api": "service_exited_nonzero",
            "ithildin-ui": "service_created",
        },
        "api_container_state_diagnostic": {
            "collection_status": "complete",
            "collection_reason_code": "api_container_state_collected",
            "cause_code": "api_application_exit_nonzero_no_engine_error",
            "health_status": "unhealthy",
        },
        "application_startup_stage_diagnostic": {
            "collection_status": "inconclusive",
            "collection_reason_code": "application_startup_stage_missing",
            "last_emitted_stage": "unknown",
        },
    }:
        failures.append("O4 Attempt 007 diagnostic classifications are not exact")
    if isinstance(diagnostic, dict) and (
        diagnostic.get("application_root_cause_known") is not False
        or diagnostic.get("marker_absence_interpretation")
        != "pre_first_checkpoint_or_unusable_diagnostic_channel"
        or diagnostic.get("cleanup_failure_codes") != []
        or diagnostic.get("diagnostic_recovery_required") is not False
    ):
        failures.append("O4 Attempt 007 diagnostic claim limits are not exact")
    receipt = disposition.get("retained_receipt")
    if not isinstance(receipt, dict) or any(
        receipt.get(key) != value
        for key, value in {
            "receipt_root": (f"{ATTEMPT_002_RECEIPT_BASE.as_posix()}/{ATTEMPT_007_RUN_ID}"),
            "receipt_root_mode": "0700",
            "disposition_size_bytes": 128,
            "disposition_sha256": ATTEMPT_007_DISPOSITION_RECEIPT_DIGEST,
            "diagnostic_size_bytes": ATTEMPT_007_DIAGNOSTIC_SIZE,
            "diagnostic_sha256": ATTEMPT_007_DIAGNOSTIC_RECEIPT_DIGEST,
            "candidate_manifest_size_bytes": ATTEMPT_007_MANIFEST_SIZE,
            "candidate_manifest_sha256": ATTEMPT_007_MANIFEST_RECEIPT_DIGEST,
            "candidate_snapshot_file_count": 664,
        }.items()
    ):
        failures.append("O4 Attempt 007 retained receipt is not exact")
    if disposition.get("tracked_closure_scope") != ATTEMPT_007_CLOSURE_CONTROL_PATH_ALLOWLIST:
        failures.append("O4 Attempt 007 closure scope is not exact")
    if not _exact_json_equal(disposition.get("authority"), CLOSED_AUTHORITY):
        failures.append("O4 Attempt 007 disposition authority is not closed")
    normalized = " ".join(document.split())
    for phrase in (
        ATTEMPT_007_CANDIDATE_COMMIT,
        ATTEMPT_007_CANDIDATE_TREE,
        ATTEMPT_007_RUN_ID,
        ATTEMPT_007_PROJECT,
        "`application_startup_stage_missing`",
        "failure before the first checkpoint or an unusable diagnostic channel",
        "does not establish a root cause",
        ATTEMPT_007_DIAGNOSTIC_RECEIPT_DIGEST,
        ATTEMPT_007_MANIFEST_RECEIPT_DIGEST,
        "all 19 authority fields are false",
        "pre-launch Docker image-readability repair investigation",
        "must not scrape logs or claim a proven root cause",
    ):
        if phrase not in normalized:
            failures.append(f"O4 Attempt 007 disposition doc is missing phrase: {phrase}")
    if _digest(document) != ATTEMPT_007_DISPOSITION_DOCUMENT_DIGEST:
        failures.append("O4 Attempt 007 disposition document digest is invalid")


def _directory_open_flags() -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return flags


def _file_open_flags() -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return flags


def _owned_exact_directory(details: os.stat_result, mode: int) -> bool:
    return (
        stat.S_ISDIR(details.st_mode)
        and stat.S_IMODE(details.st_mode) == mode
        and details.st_uid == os.geteuid()
        and details.st_gid == os.getegid()
    )


def _owned_directory(details: os.stat_result, mode: int | None = None) -> bool:
    return (
        stat.S_ISDIR(details.st_mode)
        and (mode is None or stat.S_IMODE(details.st_mode) == mode)
        and details.st_uid == os.geteuid()
        and details.st_gid == os.getegid()
    )


def _same_inode(left: os.stat_result, right: os.stat_result) -> bool:
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


def _open_owned_directory(
    path: Path,
    mode: int,
    label: str,
    failures: list[str],
) -> int | None:
    try:
        before = path.lstat()
        if not _owned_exact_directory(before, mode):
            failures.append(f"{label} is not an owner-owned {mode:04o} directory")
            return None
        descriptor = os.open(path, _directory_open_flags())
        after = os.fstat(descriptor)
    except OSError:
        failures.append(f"{label} is unavailable or not no-follow")
        return None
    if not _same_inode(before, after) or not _owned_exact_directory(after, mode):
        os.close(descriptor)
        failures.append(f"{label} changed while it was opened")
        return None
    return descriptor


def _open_repository_root(
    repo_root: Path,
    failures: list[str],
) -> int | None:
    try:
        descriptor = os.open(repo_root, _directory_open_flags())
        details = os.fstat(descriptor)
    except OSError:
        failures.append("O4 repository root is unavailable or not no-follow")
        return None
    if not _owned_directory(details):
        os.close(descriptor)
        failures.append("O4 repository root is not an owner-owned directory")
        return None
    return descriptor


def _open_owned_child_directory_optional_mode(
    parent_descriptor: int,
    name: str,
    mode: int | None,
    label: str,
    failures: list[str],
) -> int | None:
    try:
        before = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
        if not _owned_directory(before, mode):
            mode_text = "expected-mode" if mode is None else f"{mode:04o}"
            failures.append(f"{label} is not an owner-owned {mode_text} directory")
            return None
        descriptor = os.open(
            name,
            _directory_open_flags(),
            dir_fd=parent_descriptor,
        )
        after = os.fstat(descriptor)
    except OSError:
        failures.append(f"{label} is unavailable or not no-follow")
        return None
    if not _same_inode(before, after) or not _owned_directory(after, mode):
        os.close(descriptor)
        failures.append(f"{label} changed while it was opened")
        return None
    return descriptor


def _open_owned_child_directory(
    parent_descriptor: int,
    name: str,
    mode: int,
    label: str,
    failures: list[str],
) -> int | None:
    return _open_owned_child_directory_optional_mode(
        parent_descriptor,
        name,
        mode,
        label,
        failures,
    )


def _open_repo_relative_directory(
    repository_descriptor: int,
    relative: Path,
    *,
    expected_modes: dict[str, int],
    label: str,
    failures: list[str],
) -> int | None:
    if not _safe_snapshot_relative_path(relative.as_posix()):
        failures.append(f"{label} path is not a safe repository-relative path")
        return None
    current = os.dup(repository_descriptor)
    traversed: list[str] = []
    for component in relative.parts:
        traversed.append(component)
        relative_component = "/".join(traversed)
        child = _open_owned_child_directory_optional_mode(
            current,
            component,
            expected_modes.get(relative_component),
            f"{label} component {relative_component}",
            failures,
        )
        os.close(current)
        if child is None:
            return None
        current = child
    return current


def _validate_repo_relative_absence(
    repository_descriptor: int,
    relative: Path,
    *,
    expected_parent_modes: dict[str, int],
    label: str,
    failures: list[str],
) -> None:
    if not _safe_snapshot_relative_path(relative.as_posix()):
        failures.append(f"{label} path is not a safe repository-relative path")
        return
    current = os.dup(repository_descriptor)
    traversed: list[str] = []
    try:
        for component in relative.parts[:-1]:
            traversed.append(component)
            relative_component = "/".join(traversed)
            try:
                details = os.stat(
                    component,
                    dir_fd=current,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                return
            except OSError:
                failures.append(f"{label} ancestor is unavailable or ambiguous")
                return
            expected_mode = expected_parent_modes.get(relative_component)
            if not _owned_directory(details, expected_mode):
                failures.append(
                    f"{label} ancestor is not an owner-owned directory: {relative_component}"
                )
                return
            child = _open_owned_child_directory_optional_mode(
                current,
                component,
                expected_mode,
                f"{label} ancestor {relative_component}",
                failures,
            )
            if child is None:
                return
            os.close(current)
            current = child
        try:
            os.stat(
                relative.parts[-1],
                dir_fd=current,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return
        except OSError:
            failures.append(f"{label} absence is unavailable or ambiguous")
        else:
            failures.append(f"{label} is present")
    finally:
        os.close(current)


def _read_owned_child_file(
    parent_descriptor: int,
    name: str,
    *,
    mode: int,
    size: int,
    digest: str,
    label: str,
    failures: list[str],
) -> bytes | None:
    descriptor = -1
    try:
        before = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != mode
            or before.st_uid != os.geteuid()
            or before.st_gid != os.getegid()
            or before.st_size != size
        ):
            failures.append(f"{label} metadata is not exact")
            return None
        descriptor = os.open(name, _file_open_flags(), dir_fd=parent_descriptor)
        opened = os.fstat(descriptor)
        if not _same_inode(before, opened):
            failures.append(f"{label} changed while it was opened")
            return None
        content = bytearray()
        while len(content) <= size:
            chunk = os.read(descriptor, min(65536, size + 1 - len(content)))
            if not chunk:
                break
            content.extend(chunk)
        after = os.fstat(descriptor)
    except OSError:
        failures.append(f"{label} is unavailable or not a no-follow regular file")
        return None
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    raw = bytes(content)
    if (
        not _same_inode(opened, after)
        or opened.st_size != after.st_size
        or len(raw) != size
        or "sha256:" + hashlib.sha256(raw).hexdigest() != digest
    ):
        failures.append(f"{label} content or digest is not exact")
        return None
    return raw


def _safe_snapshot_relative_path(relative: object) -> bool:
    if not isinstance(relative, str) or not relative:
        return False
    path = Path(relative)
    return (
        not path.is_absolute()
        and path.as_posix() == relative
        and all(part not in {"", ".", ".."} for part in path.parts)
    )


def _candidate_snapshot_from_git(
    repo_root: Path,
    manifest_files: dict[str, JsonValue],
    failures: list[str],
    *,
    candidate_commit: str = ATTEMPT_002_CANDIDATE_COMMIT,
    label: str = "O4 Attempt 002",
) -> dict[str, tuple[int, str, bytes]]:
    try:
        listing_result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "ls-tree",
                "-rz",
                "--full-tree",
                candidate_commit,
            ],
            check=False,
            capture_output=True,
        )
    except OSError:
        failures.append(f"{label} candidate tree inventory is unavailable")
        return {}
    if listing_result.returncode != 0:
        failures.append(f"{label} candidate tree inventory is unavailable")
        return {}
    inventory: dict[str, tuple[str, str]] = {}
    for record in listing_result.stdout.split(b"\0"):
        if not record:
            continue
        try:
            raw_metadata, raw_path = record.split(b"\t", 1)
            raw_mode, raw_type, raw_oid = raw_metadata.decode("ascii").split(" ", 2)
            relative = raw_path.decode("utf-8")
        except (ValueError, UnicodeError):
            failures.append(f"{label} candidate tree inventory is ambiguous")
            return {}
        if relative in manifest_files:
            if (
                raw_type != "blob"
                or raw_mode not in {"100644", "100755"}
                or not re.fullmatch(r"[0-9a-f]{40}", raw_oid)
            ):
                failures.append(f"{label} candidate snapshot source is invalid: {relative}")
                continue
            inventory[relative] = (raw_mode, raw_oid)
    if set(inventory) != set(manifest_files):
        failures.append(f"{label} manifest paths do not match candidate blobs")
        return {}
    ordered = sorted(inventory)
    batch_input = b"".join(inventory[relative][1].encode("ascii") + b"\n" for relative in ordered)
    try:
        batch_result = subprocess.run(
            ["git", "-C", str(repo_root), "cat-file", "--batch"],
            input=batch_input,
            check=False,
            capture_output=True,
        )
    except OSError:
        failures.append(f"{label} candidate blob content is unavailable")
        return {}
    if batch_result.returncode != 0:
        failures.append(f"{label} candidate blob content is unavailable")
        return {}
    cursor = 0
    total = 0
    expected: dict[str, tuple[int, str, bytes]] = {}
    for relative in ordered:
        header_end = batch_result.stdout.find(b"\n", cursor)
        if header_end < 0:
            failures.append(f"{label} candidate blob batch is truncated")
            return {}
        header = batch_result.stdout[cursor:header_end].split()
        cursor = header_end + 1
        if (
            len(header) != 3
            or header[0].decode("ascii", errors="ignore") != inventory[relative][1]
            or header[1] != b"blob"
        ):
            failures.append(f"{label} candidate blob batch is ambiguous")
            return {}
        try:
            size = int(header[2])
        except ValueError:
            failures.append(f"{label} candidate blob size is invalid")
            return {}
        if size < 0 or size > MAX_RETAINED_SNAPSHOT_FILE_BYTES:
            failures.append(f"{label} candidate blob exceeds size ceiling: {relative}")
            return {}
        content = batch_result.stdout[cursor : cursor + size]
        cursor += size
        if len(content) != size or batch_result.stdout[cursor : cursor + 1] != b"\n":
            failures.append(f"{label} candidate blob batch is truncated")
            return {}
        cursor += 1
        total += size
        if total > MAX_RETAINED_SNAPSHOT_BYTES:
            failures.append(f"{label} candidate snapshot exceeds size ceiling")
            return {}
        snapshot_mode = 0o500 if inventory[relative][0] == "100755" else 0o400
        expected[relative] = (
            snapshot_mode,
            "sha256:" + hashlib.sha256(content).hexdigest(),
            content,
        )
    if cursor != len(batch_result.stdout):
        failures.append(f"{label} candidate blob batch has trailing output")
        return {}
    return expected


def _validate_snapshot_directory(
    descriptor: int,
    expected: dict[str, tuple[int, str, bytes]],
    failures: list[str],
    *,
    prefix: str = "",
    seen: set[str] | None = None,
    label: str = "O4 Attempt 002",
) -> set[str]:
    observed = set() if seen is None else seen
    try:
        names = sorted(os.listdir(descriptor))
    except OSError:
        failures.append(f"{label} snapshot directory cannot be enumerated")
        return observed
    expected_directories = {
        parent.as_posix()
        for relative in expected
        for parent in Path(relative).parents
        if parent != Path(".")
    }
    for name in names:
        if name in {"", ".", ".."} or "/" in name:
            failures.append(f"{label} snapshot contains an invalid entry name")
            continue
        relative = f"{prefix}/{name}" if prefix else name
        try:
            details = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
        except OSError:
            failures.append(f"{label} snapshot entry is unavailable: {relative}")
            continue
        if stat.S_ISDIR(details.st_mode):
            if relative not in expected_directories:
                failures.append(f"{label} snapshot contains an extra directory: {relative}")
            child = _open_owned_child_directory(
                descriptor,
                name,
                0o500,
                f"{label} snapshot directory {relative}",
                failures,
            )
            if child is None:
                continue
            try:
                _validate_snapshot_directory(
                    child,
                    expected,
                    failures,
                    prefix=relative,
                    seen=observed,
                    label=label,
                )
            finally:
                os.close(child)
            continue
        if not stat.S_ISREG(details.st_mode):
            failures.append(f"{label} snapshot contains a symlink or special entry: {relative}")
            continue
        expectation = expected.get(relative)
        if expectation is None:
            failures.append(f"{label} snapshot contains an extra file: {relative}")
            continue
        mode, digest, content = expectation
        actual = _read_owned_child_file(
            descriptor,
            name,
            mode=mode,
            size=len(content),
            digest=digest,
            label=f"{label} snapshot file {relative}",
            failures=failures,
        )
        if actual is not None and actual != content:
            failures.append(f"{label} snapshot file content differs: {relative}")
        observed.add(relative)
    return observed


def _validate_attempt_002_runtime_posture_from_descriptor(
    repository_descriptor: int,
    failures: list[str],
) -> None:
    runtime_base = _open_repo_relative_directory(
        repository_descriptor,
        ATTEMPT_002_RUNTIME_BASE,
        expected_modes={ATTEMPT_002_RUNTIME_BASE.as_posix(): 0o700},
        label="O4 Attempt 002 runtime base",
        failures=failures,
    )
    if runtime_base is not None:
        try:
            try:
                if sorted(os.listdir(runtime_base)) != sorted(
                    [ATTEMPT_008_RUN_ID, IMAGE_RECOVERY_CONSUMPTION_RECEIPT_NAME]
                ):
                    failures.append(
                        "O4 runtime base entries do not equal the retained Attempt 008 runtime "
                        "and recovery receipt"
                    )
            except OSError:
                failures.append("O4 retained recovery runtime base cannot be enumerated")
            attempt_008_runtime = _open_owned_child_directory(
                runtime_base,
                ATTEMPT_008_RUN_ID,
                0o700,
                "O4 Attempt 008 retained runtime root",
                failures,
            )
            if attempt_008_runtime is not None:
                os.close(attempt_008_runtime)
            receipt = _read_owned_child_file(
                runtime_base,
                IMAGE_RECOVERY_CONSUMPTION_RECEIPT_NAME,
                mode=0o600,
                size=len(IMAGE_RECOVERY_CONSUMPTION_RECEIPT_BYTES),
                digest=IMAGE_RECOVERY_CONSUMPTION_RECEIPT_DIGEST,
                label="O4 Attempt 003 image recovery consumption receipt",
                failures=failures,
            )
            if receipt is not None and receipt != IMAGE_RECOVERY_CONSUMPTION_RECEIPT_BYTES:
                failures.append(
                    "O4 Attempt 003 image recovery consumption receipt content is not exact"
                )
        finally:
            os.close(runtime_base)
    for path, parent_modes, label in (
        (
            ATTEMPT_002_RUNTIME_ROOT,
            {ATTEMPT_002_RUNTIME_BASE.as_posix(): 0o700},
            "O4 Attempt 002 runtime run directory or plaintext",
        ),
        (
            ATTEMPT_003_RUNTIME_ROOT,
            {ATTEMPT_002_RUNTIME_BASE.as_posix(): 0o700},
            "O4 Attempt 003 runtime run directory or plaintext",
        ),
        (
            ATTEMPT_004_RUNTIME_ROOT,
            {ATTEMPT_002_RUNTIME_BASE.as_posix(): 0o700},
            "O4 Attempt 004 runtime run directory or plaintext",
        ),
        (
            ATTEMPT_005_RUNTIME_ROOT,
            {ATTEMPT_002_RUNTIME_BASE.as_posix(): 0o700},
            "O4 Attempt 005 runtime run directory or plaintext",
        ),
        (
            ATTEMPT_006_RUNTIME_ROOT,
            {ATTEMPT_002_RUNTIME_BASE.as_posix(): 0o700},
            "O4 Attempt 006 runtime run directory or plaintext",
        ),
        (
            ATTEMPT_007_RUNTIME_ROOT,
            {ATTEMPT_002_RUNTIME_BASE.as_posix(): 0o700},
            "O4 Attempt 007 runtime run directory or plaintext",
        ),
        (ATTEMPT_002_REPORT_BASE, {}, "O4 published report base"),
    ):
        _validate_repo_relative_absence(
            repository_descriptor,
            path,
            expected_parent_modes=parent_modes,
            label=label,
            failures=failures,
        )


def _validate_attempt_002_runtime_posture(
    repo_root: Path,
    failures: list[str],
) -> None:
    repository_descriptor = _open_repository_root(repo_root, failures)
    if repository_descriptor is None:
        return
    try:
        _validate_attempt_002_runtime_posture_from_descriptor(
            repository_descriptor,
            failures,
        )
    finally:
        os.close(repository_descriptor)


def _validate_attempt_diagnostic_bytes(
    document: bytes,
    failures: list[str],
    *,
    attempt: int,
) -> None:
    try:
        diagnostic = json.loads(
            document.decode("utf-8"),
            object_pairs_hook=_reject_duplicates,
        )
    except (UnicodeError, json.JSONDecodeError, ValueError):
        failures.append(f"O4 Attempt {attempt:03d} failure diagnostic is ambiguous")
        return
    expected_fields = {
        "base_build_completed",
        "bound_inspected_image_identities",
        "bridge_build_completed",
        "cleanup_failure_codes",
        "highest_completed_stage",
        "outward_failure_code",
        "primary_failure_code",
        "record_type",
        "recovery_required",
        "schema_version",
    }
    if attempt in {5, 6, 7}:
        expected_fields.add("base_service_start_diagnostic")
    if not isinstance(diagnostic, dict) or set(diagnostic) != expected_fields:
        failures.append(f"O4 Attempt {attempt:03d} failure diagnostic fields are not exact")
        return
    historical_scalars: JsonObject = {
        "schema_version": "1",
        "record_type": "local_v1_lv1_003_o4_producer_failure_diagnostic",
        "base_build_completed": True,
        "bridge_build_completed": True,
        "cleanup_failure_codes": ["owned_image_id_absence_probe_failed"],
        "highest_completed_stage": 7,
        "outward_failure_code": "recovery_required",
        "primary_failure_code": "base_services_start_failed",
        "recovery_required": True,
    }
    current_scalars: JsonObject = {
        "schema_version": "1",
        "record_type": "local_v1_lv1_003_o4_producer_failure_diagnostic",
        "base_build_completed": True,
        "bridge_build_completed": True,
        "cleanup_failure_codes": [],
        "highest_completed_stage": 7,
        "outward_failure_code": "base_services_start_failed",
        "primary_failure_code": "base_services_start_failed",
        "recovery_required": False,
    }
    attempt_008_scalars: JsonObject = {
        "schema_version": "1",
        "record_type": "local_v1_lv1_003_o4_producer_failure_diagnostic",
        "base_build_completed": True,
        "bridge_build_completed": True,
        "cleanup_failure_codes": ["enrollment_outcome_ambiguous"],
        "highest_completed_stage": 7,
        "outward_failure_code": "recovery_required",
        "primary_failure_code": "subprocess_output_rejected",
        "recovery_required": True,
    }
    expected_scalars = (
        attempt_008_scalars
        if attempt == 8
        else current_scalars
        if attempt in {5, 6, 7}
        else historical_scalars
    )
    for key, expected_value in expected_scalars.items():
        if not _exact_json_equal(diagnostic.get(key), expected_value):
            failures.append(f"O4 Attempt {attempt:03d} failure diagnostic {key} is not exact")
    if attempt == 5 and not _exact_json_equal(
        diagnostic.get("base_service_start_diagnostic"),
        {
            "collection_status": "complete",
            "reason_code": "base_service_start_state_collected",
            "services": {
                "ithildin-api": "service_exited_nonzero",
                "ithildin-ui": "service_created",
            },
        },
    ):
        failures.append("O4 Attempt 005 base-service diagnostic is not exact")
    if attempt == 6 and not _exact_json_equal(
        diagnostic.get("base_service_start_diagnostic"),
        {
            "collection_status": "complete",
            "reason_code": "base_service_start_state_collected",
            "services": {
                "ithildin-api": "service_exited_nonzero",
                "ithildin-ui": "service_created",
            },
            "api_container_state_diagnostic": {
                "collection_status": "complete",
                "collection_reason_code": "api_container_state_collected",
                "cause_code": "api_application_exit_nonzero_no_engine_error",
                "health_status": "unhealthy",
            },
        },
    ):
        failures.append("O4 Attempt 006 API container-state diagnostic is not exact")
    if attempt == 7 and not _exact_json_equal(
        diagnostic.get("base_service_start_diagnostic"),
        {
            "collection_status": "complete",
            "reason_code": "base_service_start_state_collected",
            "services": {
                "ithildin-api": "service_exited_nonzero",
                "ithildin-ui": "service_created",
            },
            "api_container_state_diagnostic": {
                "collection_status": "complete",
                "collection_reason_code": "api_container_state_collected",
                "cause_code": "api_application_exit_nonzero_no_engine_error",
                "health_status": "unhealthy",
            },
            "application_startup_stage_diagnostic": {
                "collection_status": "inconclusive",
                "collection_reason_code": "application_startup_stage_missing",
                "last_emitted_stage": "unknown",
            },
        },
    ):
        failures.append("O4 Attempt 007 application startup-stage diagnostic is not exact")
    identities = diagnostic.get("bound_inspected_image_identities")
    if not isinstance(identities, list) or len(identities) != 4:
        failures.append(f"O4 Attempt {attempt:03d} bound diagnostic identities are not exact")
        return
    observed = [
        (
            identity.get("service"),
            identity.get("reference"),
            identity.get("image_id"),
            identity.get("project"),
            identity.get("platform"),
        )
        for identity in identities
        if isinstance(identity, dict)
    ]
    historical_expected = [
        (
            "ithildin-api",
            "ithildin/api-o4:329e129a",
            "sha256:493df3eb92c9196cdc11f6f69ab517e88be8a44c731343d8cd0927fd6bec2914",
            ATTEMPT_004_PROJECT,
            "linux/arm64",
        ),
        (
            "ithildin-ui",
            "ithildin/ui-o4:329e129a",
            "sha256:d3cd7f2521d07ceceb2cf1f75aaa73278215ad7bc010ff9697fa883a3693f977",
            ATTEMPT_004_PROJECT,
            "linux/arm64",
        ),
        (
            "ithildin-node",
            "ithildin/node-o4:329e129a",
            "sha256:c5f7368093d2735e060f9337c0be2a9654a8f515c59f4bf8dfe5c37b57095933",
            ATTEMPT_004_PROJECT,
            "linux/arm64",
        ),
        (
            "hermes",
            "ithildin/hermes-node-bridge-o4:329e129a",
            "sha256:048653b7091ceee199cbb1b6c0b47f1420a663fd1610fff340cc8378fc5610c1",
            ATTEMPT_004_PROJECT,
            "linux/arm64",
        ),
    ]
    current_expected = [
        (
            "ithildin-api",
            "ithildin/api-o4:b806c1bd",
            "sha256:e4ca0c62c670f38f150bb09f42a356e0d5b2956cf7cb56a3bd729004a1ffcb33",
            ATTEMPT_005_PROJECT,
            "linux/arm64",
        ),
        (
            "ithildin-ui",
            "ithildin/ui-o4:b806c1bd",
            "sha256:a1e78335549b50210d6f607dc0335e0263d60fc2d9ff5e4e9ac6a303af3b9b38",
            ATTEMPT_005_PROJECT,
            "linux/arm64",
        ),
        (
            "ithildin-node",
            "ithildin/node-o4:b806c1bd",
            "sha256:a876ac0a41cd64e57c5b6f28839363d831187323733280929a74ffe27a0e8294",
            ATTEMPT_005_PROJECT,
            "linux/arm64",
        ),
        (
            "hermes",
            "ithildin/hermes-node-bridge-o4:b806c1bd",
            "sha256:702bd8613619440585ff6f2011c2e49fb07aed587223eab9d2298604e775ebf9",
            ATTEMPT_005_PROJECT,
            "linux/arm64",
        ),
    ]
    attempt_006_expected = [
        (
            "ithildin-api",
            "ithildin/api-o4:b00570b3",
            "sha256:e75264be1cf08effff08d122324410435955dd6c816c506f1b1d5da5614527a5",
            ATTEMPT_006_PROJECT,
            "linux/arm64",
        ),
        (
            "ithildin-ui",
            "ithildin/ui-o4:b00570b3",
            "sha256:2d97d8658498978da4ca610dbd51e0b6aa55bf9b35f0815a002b65054a208ce5",
            ATTEMPT_006_PROJECT,
            "linux/arm64",
        ),
        (
            "ithildin-node",
            "ithildin/node-o4:b00570b3",
            "sha256:1ae93646eca07cf3472ea70952ee83083228eb1924aebf91ab6fa0cd54cb0ebb",
            ATTEMPT_006_PROJECT,
            "linux/arm64",
        ),
        (
            "hermes",
            "ithildin/hermes-node-bridge-o4:b00570b3",
            "sha256:1a1eb3d53d106428f1266e8ce1d1799fd6b6074449673767a2a2016da647794f",
            ATTEMPT_006_PROJECT,
            "linux/arm64",
        ),
    ]
    attempt_008_expected = [
        (
            "ithildin-api",
            "ithildin/api-o4:d801f37b",
            "sha256:20edad55b1bc2a67f6aa02c164122cdfc54ef139c4628e9ed9043936b9114242",
            ATTEMPT_008_PROJECT,
            "linux/arm64",
        ),
        (
            "ithildin-ui",
            "ithildin/ui-o4:d801f37b",
            "sha256:c3f77a6d09fad1df44dbd2506a2b92ba437bb3d2fead2d43040019b2ff69a27c",
            ATTEMPT_008_PROJECT,
            "linux/arm64",
        ),
        (
            "ithildin-node",
            "ithildin/node-o4:d801f37b",
            "sha256:74dcb8a496ce2780b23ac7947aa821094fc80688a35a2c4318302e48809c3390",
            ATTEMPT_008_PROJECT,
            "linux/arm64",
        ),
        (
            "hermes",
            "ithildin/hermes-node-bridge-o4:d801f37b",
            "sha256:3eb87a25a51b1182882588f5271705886e9fcf660742ba9006d26d91f6555c3e",
            ATTEMPT_008_PROJECT,
            "linux/arm64",
        ),
    ]
    expected_identities = (
        attempt_008_expected
        if attempt == 8
        else [
            (
                "ithildin-api",
                "ithildin/api-o4:1993a10f",
                "sha256:686096ac390a1d3d169c8a146d873b08d9fde05d96a7b6ea78a40d47d6aa6b03",
                ATTEMPT_007_PROJECT,
                "linux/arm64",
            ),
            (
                "ithildin-ui",
                "ithildin/ui-o4:1993a10f",
                "sha256:8eb20fbc8457db83d7a127b630b01fb93323eedc4b4d7a745e534bd21b88a11d",
                ATTEMPT_007_PROJECT,
                "linux/arm64",
            ),
            (
                "ithildin-node",
                "ithildin/node-o4:1993a10f",
                "sha256:1839df6ce76622b08a4dedf3abf63da4dcdcd02086ffec2683bf808fdf79c141",
                ATTEMPT_007_PROJECT,
                "linux/arm64",
            ),
            (
                "hermes",
                "ithildin/hermes-node-bridge-o4:1993a10f",
                "sha256:a0ab24b39cfc2ad24051004278c347ce86c3a1fb865724f0340e96365f6e958f",
                ATTEMPT_007_PROJECT,
                "linux/arm64",
            ),
        ]
        if attempt == 7
        else attempt_006_expected
        if attempt == 6
        else current_expected
        if attempt == 5
        else historical_expected
    )
    if observed != expected_identities:
        failures.append(f"O4 Attempt {attempt:03d} bound diagnostic image identities differ")


def _validate_retained_attempt_receipt(
    repo_root: Path,
    receipt_base: int,
    failures: list[str],
    *,
    label: str,
    run_id: str,
    disposition_bytes: bytes,
    disposition_digest: str,
    manifest_size: int,
    manifest_digest: str,
    candidate_commit: str,
    candidate_tree: str,
    snapshot_file_count: int,
    diagnostic_size: int | None = None,
    diagnostic_digest: str | None = None,
    diagnostic_attempt: int | None = None,
) -> None:
    receipt_root = _open_owned_child_directory(
        receipt_base,
        run_id,
        0o700,
        f"{label} receipt root",
        failures,
    )
    if receipt_root is None:
        return
    snapshot: int | None = None
    diagnostic_bytes: bytes | None = None
    try:
        try:
            expected_entries = [
                "candidate",
                "candidate-manifest.json",
                "disposition.json",
            ]
            if diagnostic_size is not None or diagnostic_digest is not None:
                expected_entries.append("diagnostic.json")
            if sorted(os.listdir(receipt_root)) != sorted(expected_entries):
                failures.append(f"{label} receipt root entries are not exact")
        except OSError:
            failures.append(f"{label} receipt root cannot be enumerated")
        disposition = _read_owned_child_file(
            receipt_root,
            "disposition.json",
            mode=0o600,
            size=len(disposition_bytes),
            digest=disposition_digest,
            label=f"{label} quarantine disposition",
            failures=failures,
        )
        if disposition is not None and disposition != disposition_bytes:
            failures.append(f"{label} quarantine disposition content is not exact")
        if diagnostic_size is not None and diagnostic_digest is not None:
            diagnostic_bytes = _read_owned_child_file(
                receipt_root,
                "diagnostic.json",
                mode=0o600,
                size=diagnostic_size,
                digest=diagnostic_digest,
                label=f"{label} failure diagnostic",
                failures=failures,
            )
        manifest_bytes = _read_owned_child_file(
            receipt_root,
            "candidate-manifest.json",
            mode=0o600,
            size=manifest_size,
            digest=manifest_digest,
            label=f"{label} candidate manifest",
            failures=failures,
        )
        snapshot = _open_owned_child_directory(
            receipt_root,
            "candidate",
            0o500,
            f"{label} snapshot root",
            failures,
        )
    finally:
        os.close(receipt_root)
    if diagnostic_size is not None or diagnostic_digest is not None:
        if diagnostic_size is None or diagnostic_digest is None:
            failures.append(f"{label} diagnostic expectation is incomplete")
        elif diagnostic_bytes is None:
            failures.append(f"{label} failure diagnostic is unavailable")
        else:
            if diagnostic_attempt is None:
                failures.append(f"{label} diagnostic attempt identity is unavailable")
            else:
                _validate_attempt_diagnostic_bytes(
                    diagnostic_bytes,
                    failures,
                    attempt=diagnostic_attempt,
                )
    if manifest_bytes is None or snapshot is None:
        if snapshot is not None:
            os.close(snapshot)
        return
    try:
        try:
            manifest = json.loads(
                manifest_bytes.decode("utf-8"),
                object_pairs_hook=_reject_duplicates,
            )
        except (UnicodeError, json.JSONDecodeError, ValueError):
            failures.append(f"{label} candidate manifest is ambiguous")
            return
        if not isinstance(manifest, dict) or set(manifest) != {
            "candidate_commit",
            "candidate_tree",
            "files",
        }:
            failures.append(f"{label} candidate manifest fields are not exact")
            return
        if (
            manifest.get("candidate_commit") != candidate_commit
            or manifest.get("candidate_tree") != candidate_tree
        ):
            failures.append(f"{label} candidate manifest identity is not exact")
        raw_files = manifest.get("files")
        if not isinstance(raw_files, dict) or len(raw_files) != snapshot_file_count:
            failures.append(f"{label} candidate manifest file count is not exact")
            return
        manifest_files = cast(dict[str, JsonValue], raw_files)
        for relative, value in manifest_files.items():
            if (
                not _safe_snapshot_relative_path(relative)
                or not isinstance(value, dict)
                or set(value) != {"mode", "sha256"}
                or type(value.get("mode")) is not int
                or value.get("mode") not in {0o400, 0o500}
                or not isinstance(value.get("sha256"), str)
                or re.fullmatch(
                    r"sha256:[0-9a-f]{64}",
                    cast(str, value.get("sha256")),
                )
                is None
            ):
                failures.append(f"{label} candidate manifest entry is invalid: {relative}")
        expected = _candidate_snapshot_from_git(
            repo_root,
            manifest_files,
            failures,
            candidate_commit=candidate_commit,
            label=label,
        )
        if len(expected) != snapshot_file_count:
            return
        for relative, (mode, digest, _) in expected.items():
            value = manifest_files[relative]
            if (
                not isinstance(value, dict)
                or not _exact_json_equal(value.get("mode"), mode)
                or not _exact_json_equal(value.get("sha256"), digest)
            ):
                failures.append(f"{label} candidate manifest binding differs: {relative}")
        observed = _validate_snapshot_directory(
            snapshot,
            expected,
            failures,
            label=label,
        )
        if observed != set(expected):
            failures.append(f"{label} snapshot file inventory is not exact")
        if len(observed) != snapshot_file_count:
            failures.append(f"{label} snapshot file count is not exact")
    finally:
        os.close(snapshot)


def _validate_retained_attempt_evidence(
    repo_root: Path,
    failures: list[str],
) -> None:
    repository_descriptor = _open_repository_root(repo_root, failures)
    if repository_descriptor is None:
        return
    _validate_attempt_002_runtime_posture_from_descriptor(
        repository_descriptor,
        failures,
    )
    receipt_base = _open_repo_relative_directory(
        repository_descriptor,
        ATTEMPT_002_RECEIPT_BASE,
        expected_modes={ATTEMPT_002_RECEIPT_BASE.as_posix(): 0o700},
        label="O4 retained receipt base",
        failures=failures,
    )
    os.close(repository_descriptor)
    if receipt_base is None:
        return
    try:
        try:
            expected_runs = sorted(
                [
                    ATTEMPT_002_RUN_ID,
                    ATTEMPT_003_RUN_ID,
                    ATTEMPT_004_RUN_ID,
                    ATTEMPT_005_RUN_ID,
                    ATTEMPT_006_RUN_ID,
                    ATTEMPT_007_RUN_ID,
                    ATTEMPT_008_RUN_ID,
                ]
            )
            if sorted(os.listdir(receipt_base)) != expected_runs:
                failures.append("O4 retained receipt base entries are not exact")
        except OSError:
            failures.append("O4 retained receipt base cannot be enumerated")
        _validate_retained_attempt_receipt(
            repo_root,
            receipt_base,
            failures,
            label="O4 Attempt 002",
            run_id=ATTEMPT_002_RUN_ID,
            disposition_bytes=ATTEMPT_002_DISPOSITION_BYTES,
            disposition_digest=ATTEMPT_002_DISPOSITION_RECEIPT_DIGEST,
            manifest_size=ATTEMPT_002_MANIFEST_SIZE,
            manifest_digest=ATTEMPT_002_MANIFEST_RECEIPT_DIGEST,
            candidate_commit=ATTEMPT_002_CANDIDATE_COMMIT,
            candidate_tree=ATTEMPT_002_CANDIDATE_TREE,
            snapshot_file_count=ATTEMPT_002_SNAPSHOT_FILE_COUNT,
        )
        _validate_retained_attempt_receipt(
            repo_root,
            receipt_base,
            failures,
            label="O4 Attempt 003",
            run_id=ATTEMPT_003_RUN_ID,
            disposition_bytes=ATTEMPT_003_DISPOSITION_BYTES,
            disposition_digest=ATTEMPT_003_DISPOSITION_RECEIPT_DIGEST,
            manifest_size=ATTEMPT_003_MANIFEST_SIZE,
            manifest_digest=ATTEMPT_003_MANIFEST_RECEIPT_DIGEST,
            candidate_commit=ATTEMPT_003_CANDIDATE_COMMIT,
            candidate_tree=ATTEMPT_003_CANDIDATE_TREE,
            snapshot_file_count=ATTEMPT_003_SNAPSHOT_FILE_COUNT,
        )
        _validate_retained_attempt_receipt(
            repo_root,
            receipt_base,
            failures,
            label="O4 Attempt 004",
            run_id=ATTEMPT_004_RUN_ID,
            disposition_bytes=ATTEMPT_003_DISPOSITION_BYTES,
            disposition_digest=ATTEMPT_004_DISPOSITION_RECEIPT_DIGEST,
            manifest_size=ATTEMPT_004_MANIFEST_SIZE,
            manifest_digest=ATTEMPT_004_MANIFEST_RECEIPT_DIGEST,
            candidate_commit=ATTEMPT_004_CANDIDATE_COMMIT,
            candidate_tree=ATTEMPT_004_CANDIDATE_TREE,
            snapshot_file_count=ATTEMPT_004_SNAPSHOT_FILE_COUNT,
            diagnostic_size=ATTEMPT_004_DIAGNOSTIC_SIZE,
            diagnostic_digest=ATTEMPT_004_DIAGNOSTIC_RECEIPT_DIGEST,
            diagnostic_attempt=4,
        )
        _validate_retained_attempt_receipt(
            repo_root,
            receipt_base,
            failures,
            label="O4 Attempt 005",
            run_id=ATTEMPT_005_RUN_ID,
            disposition_bytes=ATTEMPT_005_DISPOSITION_BYTES,
            disposition_digest=ATTEMPT_005_DISPOSITION_RECEIPT_DIGEST,
            manifest_size=ATTEMPT_005_MANIFEST_SIZE,
            manifest_digest=ATTEMPT_005_MANIFEST_RECEIPT_DIGEST,
            candidate_commit=ATTEMPT_005_CANDIDATE_COMMIT,
            candidate_tree=ATTEMPT_005_CANDIDATE_TREE,
            snapshot_file_count=ATTEMPT_005_SNAPSHOT_FILE_COUNT,
            diagnostic_size=ATTEMPT_005_DIAGNOSTIC_SIZE,
            diagnostic_digest=ATTEMPT_005_DIAGNOSTIC_RECEIPT_DIGEST,
            diagnostic_attempt=5,
        )
        _validate_retained_attempt_receipt(
            repo_root,
            receipt_base,
            failures,
            label="O4 Attempt 006",
            run_id=ATTEMPT_006_RUN_ID,
            disposition_bytes=ATTEMPT_006_DISPOSITION_BYTES,
            disposition_digest=ATTEMPT_006_DISPOSITION_RECEIPT_DIGEST,
            manifest_size=ATTEMPT_006_MANIFEST_SIZE,
            manifest_digest=ATTEMPT_006_MANIFEST_RECEIPT_DIGEST,
            candidate_commit=ATTEMPT_006_CANDIDATE_COMMIT,
            candidate_tree=ATTEMPT_006_CANDIDATE_TREE,
            snapshot_file_count=ATTEMPT_006_SNAPSHOT_FILE_COUNT,
            diagnostic_size=ATTEMPT_006_DIAGNOSTIC_SIZE,
            diagnostic_digest=ATTEMPT_006_DIAGNOSTIC_RECEIPT_DIGEST,
            diagnostic_attempt=6,
        )
        _validate_retained_attempt_receipt(
            repo_root,
            receipt_base,
            failures,
            label="O4 Attempt 007",
            run_id=ATTEMPT_007_RUN_ID,
            disposition_bytes=ATTEMPT_007_DISPOSITION_BYTES,
            disposition_digest=ATTEMPT_007_DISPOSITION_RECEIPT_DIGEST,
            manifest_size=ATTEMPT_007_MANIFEST_SIZE,
            manifest_digest=ATTEMPT_007_MANIFEST_RECEIPT_DIGEST,
            candidate_commit=ATTEMPT_007_CANDIDATE_COMMIT,
            candidate_tree=ATTEMPT_007_CANDIDATE_TREE,
            snapshot_file_count=ATTEMPT_007_SNAPSHOT_FILE_COUNT,
            diagnostic_size=ATTEMPT_007_DIAGNOSTIC_SIZE,
            diagnostic_digest=ATTEMPT_007_DIAGNOSTIC_RECEIPT_DIGEST,
            diagnostic_attempt=7,
        )
        _validate_retained_attempt_receipt(
            repo_root,
            receipt_base,
            failures,
            label="O4 Attempt 008",
            run_id=ATTEMPT_008_RUN_ID,
            disposition_bytes=ATTEMPT_008_DISPOSITION_BYTES,
            disposition_digest=ATTEMPT_008_DISPOSITION_RECEIPT_DIGEST,
            manifest_size=ATTEMPT_008_MANIFEST_SIZE,
            manifest_digest=ATTEMPT_008_MANIFEST_RECEIPT_DIGEST,
            candidate_commit=ATTEMPT_008_CANDIDATE_COMMIT,
            candidate_tree=ATTEMPT_008_CANDIDATE_TREE,
            snapshot_file_count=ATTEMPT_008_SNAPSHOT_FILE_COUNT,
            diagnostic_size=ATTEMPT_008_DIAGNOSTIC_SIZE,
            diagnostic_digest=ATTEMPT_008_DIAGNOSTIC_RECEIPT_DIGEST,
            diagnostic_attempt=8,
        )
    finally:
        os.close(receipt_base)


def _validate_retained_attempt_002_evidence(
    repo_root: Path,
    failures: list[str],
) -> None:
    """Backward-compatible test entrypoint for all currently retained attempts."""
    _validate_retained_attempt_evidence(repo_root, failures)


def _validate_evidence_ignore_patterns(
    repo_root: Path,
    failures: list[str],
) -> None:
    document = _read_text(repo_root / ".gitignore", failures)
    lines = document.splitlines()
    for pattern in EVIDENCE_IGNORE_PATTERNS:
        if lines.count(pattern) != 1:
            failures.append(f"O4 evidence ignore pattern is not exact: {pattern}")
    if any(line.strip() in {"var/*", "/var/*", "var/**", "/var/**"} for line in lines):
        failures.append("O4 evidence ignore posture contains a broad var pattern")


def _validate_bound_documents(repo_root: Path, failures: list[str]) -> None:
    for path, expected, label in (
        (PRODUCER_EXACT_REVIEW, PRODUCER_EXACT_REVIEW_DIGEST, "producer exact review"),
        (DISPOSITION_JSON, DISPOSITION_JSON_DIGEST, "post-review disposition JSON"),
        (
            DISPOSITION_DOCUMENT,
            DISPOSITION_DOCUMENT_DIGEST,
            "post-review disposition document",
        ),
        (
            ATTEMPT_001_DISPOSITION_JSON,
            ATTEMPT_001_DISPOSITION_JSON_DIGEST,
            "Attempt 001 disposition JSON",
        ),
        (
            ATTEMPT_001_DISPOSITION_DOCUMENT,
            ATTEMPT_001_DISPOSITION_DOCUMENT_DIGEST,
            "Attempt 001 disposition document",
        ),
        (
            ENTRYPOINT_REPAIR_REVIEW,
            ENTRYPOINT_REPAIR_REVIEW_DIGEST,
            "entrypoint repair exact review",
        ),
        (
            ATTEMPT_002_DISPOSITION_JSON,
            ATTEMPT_002_DISPOSITION_JSON_DIGEST,
            "Attempt 002 disposition JSON",
        ),
        (
            ATTEMPT_002_DISPOSITION_DOCUMENT,
            ATTEMPT_002_DISPOSITION_DOCUMENT_DIGEST,
            "Attempt 002 disposition document",
        ),
        (
            ATTEMPT_002_CLOSURE_JSON,
            ATTEMPT_002_CLOSURE_JSON_DIGEST,
            "Attempt 002 closure JSON",
        ),
        (
            ATTEMPT_002_CLOSURE_DOCUMENT,
            ATTEMPT_002_CLOSURE_DOCUMENT_DIGEST,
            "Attempt 002 closure document",
        ),
        (
            COMPOSE_REPAIR_REVIEW,
            COMPOSE_REPAIR_REVIEW_DIGEST,
            "Compose repair exact review",
        ),
        (
            ATTEMPT_003_DISPOSITION_JSON,
            ATTEMPT_003_DISPOSITION_JSON_DIGEST,
            "Attempt 003 disposition JSON",
        ),
        (
            ATTEMPT_003_DISPOSITION_DOCUMENT,
            ATTEMPT_003_DISPOSITION_DOCUMENT_DIGEST,
            "Attempt 003 disposition document",
        ),
        (
            ATTEMPT_003_CLOSURE_JSON,
            ATTEMPT_003_CLOSURE_JSON_DIGEST,
            "Attempt 003 closure JSON",
        ),
        (
            ATTEMPT_003_CLOSURE_DOCUMENT,
            ATTEMPT_003_CLOSURE_DOCUMENT_DIGEST,
            "Attempt 003 closure document",
        ),
        (
            IMAGE_RECOVERY_AUTHORIZATION,
            IMAGE_RECOVERY_AUTHORIZATION_DIGEST,
            "image recovery authorization JSON",
        ),
        (
            IMAGE_RECOVERY_AUTHORIZATION_DOCUMENT,
            IMAGE_RECOVERY_AUTHORIZATION_DOCUMENT_DIGEST,
            "image recovery authorization document",
        ),
        (
            IMAGE_RECOVERY_CLOSURE,
            IMAGE_RECOVERY_CLOSURE_DIGEST,
            "image recovery closure JSON",
        ),
        (
            IMAGE_RECOVERY_CLOSURE_DOCUMENT,
            IMAGE_RECOVERY_CLOSURE_DOCUMENT_DIGEST,
            "image recovery closure document",
        ),
        (
            RUNTIME_NATIVE_REPAIR_REVIEW,
            RUNTIME_NATIVE_REPAIR_REVIEW_DIGEST,
            "runtime-native repair exact review",
        ),
        (
            ATTEMPT_004_DISPOSITION_JSON,
            ATTEMPT_004_DISPOSITION_JSON_DIGEST,
            "Attempt 004 disposition JSON",
        ),
        (
            ATTEMPT_004_DISPOSITION_DOCUMENT,
            ATTEMPT_004_DISPOSITION_DOCUMENT_DIGEST,
            "Attempt 004 disposition document",
        ),
        (
            DIAGNOSTIC_REPAIR_REVIEW,
            DIAGNOSTIC_REPAIR_REVIEW_DIGEST,
            "diagnostic repair exact review",
        ),
        (
            ATTEMPT_005_DISPOSITION_JSON,
            ATTEMPT_005_DISPOSITION_JSON_DIGEST,
            "Attempt 005 disposition JSON",
        ),
        (
            ATTEMPT_005_DISPOSITION_DOCUMENT,
            ATTEMPT_005_DISPOSITION_DOCUMENT_DIGEST,
            "Attempt 005 disposition document",
        ),
        (
            API_CONTAINER_STATE_DIAGNOSTIC_REVIEW,
            API_CONTAINER_STATE_DIAGNOSTIC_REVIEW_DIGEST,
            "API container-state diagnostic exact review",
        ),
        (
            ATTEMPT_006_DISPOSITION_JSON,
            ATTEMPT_006_DISPOSITION_JSON_DIGEST,
            "Attempt 006 disposition JSON",
        ),
        (
            ATTEMPT_006_DISPOSITION_DOCUMENT,
            ATTEMPT_006_DISPOSITION_DOCUMENT_DIGEST,
            "Attempt 006 disposition document",
        ),
        (
            APPLICATION_STARTUP_STAGE_DIAGNOSTIC_REVIEW,
            APPLICATION_STARTUP_STAGE_DIAGNOSTIC_REVIEW_DIGEST,
            "application startup-stage diagnostic exact review",
        ),
        (
            ATTEMPT_007_DISPOSITION_JSON,
            ATTEMPT_007_DISPOSITION_JSON_DIGEST,
            "Attempt 007 disposition JSON",
        ),
        (
            ATTEMPT_007_DISPOSITION_DOCUMENT,
            ATTEMPT_007_DISPOSITION_DOCUMENT_DIGEST,
            "Attempt 007 disposition document",
        ),
        (
            IMAGE_READABILITY_REPAIR_REVIEW,
            IMAGE_READABILITY_REPAIR_REVIEW_DIGEST,
            "image-readability repair exact review",
        ),
        (
            ATTEMPT_008_DISPOSITION_JSON,
            ATTEMPT_008_DISPOSITION_JSON_DIGEST,
            "Attempt 008 disposition JSON",
        ),
        (
            ATTEMPT_008_DISPOSITION_DOCUMENT,
            ATTEMPT_008_DISPOSITION_DOCUMENT_DIGEST,
            "Attempt 008 disposition document",
        ),
        (
            ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REVIEW,
            ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REVIEW_DIGEST,
            "enrollment-output projection repair exact review",
        ),
    ):
        if _file_digest(repo_root / path, failures) != expected:
            failures.append(f"O4 {label} digest is invalid")


def _validate_execution_checkout(
    repo_root: Path,
    failures: list[str],
    *,
    candidate_parent_commit: str = ENROLLMENT_OUTPUT_PROJECTION_REPAIR_COMMIT,
    candidate_parent_tree: str = ENROLLMENT_OUTPUT_PROJECTION_REPAIR_TREE,
    reviewed_commit: str = ENROLLMENT_OUTPUT_PROJECTION_REPAIR_COMMIT,
    runtime_paths: list[str] | None = None,
    control_paths: list[str] | None = None,
    repair_paths: list[str] | None = None,
) -> tuple[str, str] | None:
    runtime_paths = (
        list(code_authorization.ALLOWED_RUNTIME_PATHS) if runtime_paths is None else runtime_paths
    )
    control_paths = ATTEMPT_009_CONTROL_PATH_ALLOWLIST if control_paths is None else control_paths
    repair_paths = [] if repair_paths is None else repair_paths
    head = _git(repo_root, ["rev-parse", "HEAD"], failures)
    tree = _git(repo_root, ["show", "-s", "--format=%T", "HEAD"], failures)
    parents = _git(repo_root, ["show", "-s", "--format=%P", "HEAD"], failures).split()
    if parents != [candidate_parent_commit]:
        failures.append(
            "O4 execution checkout is not a single immediate child of the authorized parent"
        )
    parent_tree = _git(
        repo_root,
        ["show", "-s", "--format=%T", candidate_parent_commit],
        failures,
    )
    if parent_tree != candidate_parent_tree:
        failures.append("O4 execution candidate parent tree is not exact")
    status = _git(
        repo_root,
        ["status", "--porcelain=v1", "--untracked-files=all"],
        failures,
    )
    if status:
        failures.append("O4 execution checkout is not clean")
    changed = _git(
        repo_root,
        ["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
        failures,
    ).splitlines()
    if changed != control_paths:
        failures.append("O4 execution candidate changed paths are not the exact control allowlist")
    parity = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "diff",
            "--quiet",
            reviewed_commit,
            "HEAD",
            "--",
            *runtime_paths,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if parity.returncode != 0:
        failures.append("O4 execution runtime differs from the exact reviewed candidate")
    if repair_paths:
        repair_parity = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "diff",
                "--quiet",
                candidate_parent_commit,
                "HEAD",
                "--",
                *repair_paths,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if repair_parity.returncode != 0:
            failures.append("O4 reviewed repair differs from the exact candidate parent")
    if failures:
        return None
    return head, tree


def _validate_prior_attempt_posture(repo_root: Path, failures: list[str]) -> None:
    for relative in PRIOR_ATTEMPT_ROOTS:
        path = repo_root / relative
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            continue
        except OSError:
            failures.append(f"O4 prior-attempt root is unreadable: {relative}")
            continue
        if path.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
            failures.append(f"O4 prior-attempt root is not a no-follow directory: {relative}")
            continue
        if metadata.st_uid != os.getuid() or metadata.st_gid != os.getgid():
            failures.append(f"O4 prior-attempt root ownership is unsafe: {relative}")
        if stat.S_IMODE(metadata.st_mode) != 0o700:
            failures.append(f"O4 prior-attempt root mode is not 0700: {relative}")
        try:
            retained = next(path.iterdir(), None)
        except OSError:
            failures.append(f"O4 prior-attempt root cannot be enumerated: {relative}")
            continue
        if retained is not None:
            failures.append(f"O4 prior attempt or success evidence exists: {relative}")


def _validate_wiring(repo_root: Path, failures: list[str]) -> None:
    makefile = _read_text(repo_root / "Makefile", failures)
    readme = _read_text(repo_root / "README.md", failures)
    expected_bodies = {
        AUTHORIZATION_TARGET: (
            "\tuv run python scripts/local_v1_lv1_003_o4_execution_authorization_check.py"
        ),
        PRODUCER_STATIC_TARGET: (
            "\tuv run pytest \\\n"
            "\t\ttests/test_local_v1_lv1_003_o4_execution_authorization_check.py \\\n"
            "\t\ttests/test_local_v1_lv1_003_o4_producer.py \\\n"
            "\t\ttests/test_local_v1_constrained_mission_journey.py \\\n"
            "\t\t-q"
        ),
    }
    for target, expected_body in expected_bodies.items():
        definitions = sum(line.startswith(f"{target}:") for line in makefile.splitlines())
        if definitions != 1:
            failures.append(f"O4 execution Make target is not unique: {target}")
            continue
        body = _target_body(makefile, target)
        if body.strip() != expected_body.strip():
            failures.append(f"O4 execution Make target body is not exact: {target}")
        milestone = _target_body(makefile, "local-v1-milestone-check")
        if milestone.count(f"\t$(MAKE) {target}") != 1:
            failures.append(f"O4 execution target is not in Local-v1 milestone once: {target}")
        release_header = next(
            (line for line in makefile.splitlines() if line.startswith("release-check:")),
            "",
        )
        if target in release_header:
            failures.append(f"O4 execution target must not be wired into release-check: {target}")
    run_occurrences = [
        (line_number, line)
        for line_number, line in enumerate(makefile.splitlines(), start=1)
        if PRODUCER_RUN_TARGET in line
    ]
    allowed_occurrences = 0
    for line_number, line in run_occurrences:
        if line == f"{PRODUCER_RUN_TARGET}:":
            allowed_occurrences += 1
            continue
        if line.startswith(".PHONY:"):
            tokens = line.split()
            if tokens.count(PRODUCER_RUN_TARGET) == 1 and line.count(PRODUCER_RUN_TARGET) == 1:
                allowed_occurrences += 1
                continue
        failures.append(
            "O4 live producer Make target token occurs outside its exact PHONY token "
            f"or target header: line {line_number}"
        )
    if len(run_occurrences) != 2 or allowed_occurrences != 2:
        failures.append("O4 live producer Make target occurrence allowlist is not exact")
    run_definitions = sum(line == f"{PRODUCER_RUN_TARGET}:" for line in makefile.splitlines())
    if run_definitions != 1:
        failures.append("O4 live producer Make target header is not unique and exact")
    if _target_body(makefile, PRODUCER_RUN_TARGET).strip() != (PRODUCER_MODULE_INVOCATION):
        failures.append("O4 live producer Make target body is not exact")
    if makefile.splitlines().count(PRODUCER_RUN_COMMENT) != 1:
        failures.append("O4 live producer Make target comment is not exact")
    for parent_target in (
        "release-check",
        "local-v1-milestone-check",
        PRODUCER_STATIC_TARGET,
        AUTHORIZATION_TARGET,
    ):
        if PRODUCER_RUN_TARGET in _target_body(makefile, parent_target):
            failures.append(
                f"O4 live producer target is wired into forbidden target: {parent_target}"
            )
    if "local-v1-lv1-003-o4-execution-authorization.md" not in readme:
        failures.append("README does not navigate to the O4 execution authorization")
    if "local-v1-lv1-003-o4-producer-contract.md" not in readme:
        failures.append("README does not navigate to the O4 producer contract")
    if "local-v1-lv1-003-o4-execution-authorization-check" not in readme:
        failures.append("README does not document the O4 execution authorization check")
    if "local-v1-lv1-003-o4-producer-static-check" not in readme:
        failures.append("README does not document the O4 producer static check")
    if PRODUCER_RUN_TARGET not in readme:
        failures.append("README does not document the O4 live producer entrypoint")
    if PRODUCER_MODULE_INVOCATION not in readme:
        failures.append("README does not bind the O4 module invocation")
    for phrase in (
        "Attempt 009 exact-child one-shot authorization",
        "one attempt budget",
        "retained Attempt 001-008 and recovery evidence",
        "recovery required with no cleanup or Docker-absence claim",
        "without retained raw-stdout proof",
        "Attempt 008 remains consumed",
        "separately reviewed enrollment-output projection repair",
        "new isolated attempt, not a retry, cleanup, revocation, or reconciliation",
        "producer-generated fresh run and project identity",
        "preflight fails closed before live work",
        "exactly five bounded live authority fields true and the other 14 false",
        "It is not part of release, milestone, or static checks",
        "producer contract itself grants no execution authority",
        "release and UAT remain false",
    ):
        if phrase not in readme:
            failures.append(f"README is missing current O4 Attempt 009 guidance: {phrase}")


def _target_body(makefile: str, target: str) -> str:
    lines = makefile.splitlines()
    start = next(
        (index for index, line in enumerate(lines) if line.startswith(f"{target}:")),
        None,
    )
    if start is None:
        return ""
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line and not line.startswith(("\t", " ")):
            break
        body.append(line)
    return "\n".join(body).rstrip()


def _validate_git_bindings(repo_root: Path, failures: list[str]) -> None:
    for commit, expected_tree in (
        (REVIEWED_IMPLEMENTATION_COMMIT, REVIEWED_IMPLEMENTATION_TREE),
        (CODE_AUTHORIZATION_ORIGIN_COMMIT, CODE_AUTHORIZATION_ORIGIN_TREE),
        (CODE_AUTHORIZATION_COMMIT, CODE_AUTHORIZATION_TREE),
        (ENTRYPOINT_REPAIR_COMMIT, ENTRYPOINT_REPAIR_TREE),
        (COMPOSE_REPAIR_COMMIT, COMPOSE_REPAIR_TREE),
        (IMAGE_RECOVERY_CANDIDATE_COMMIT, IMAGE_RECOVERY_CANDIDATE_TREE),
        (IMAGE_RECOVERY_CLOSURE_COMMIT, IMAGE_RECOVERY_CLOSURE_TREE),
        (RUNTIME_NATIVE_REPAIR_COMMIT, RUNTIME_NATIVE_REPAIR_TREE),
        (ATTEMPT_004_CANDIDATE_COMMIT, ATTEMPT_004_CANDIDATE_TREE),
        (ATTEMPT_004_CLOSURE_COMMIT, ATTEMPT_004_CLOSURE_TREE),
        (DIAGNOSTIC_REPAIR_COMMIT, DIAGNOSTIC_REPAIR_TREE),
        (ATTEMPT_005_CANDIDATE_COMMIT, ATTEMPT_005_CANDIDATE_TREE),
        (ATTEMPT_005_CLOSURE_COMMIT, ATTEMPT_005_CLOSURE_TREE),
        (
            API_CONTAINER_STATE_DIAGNOSTIC_REJECTED_001_COMMIT,
            API_CONTAINER_STATE_DIAGNOSTIC_REJECTED_001_TREE,
        ),
        (
            API_CONTAINER_STATE_DIAGNOSTIC_REJECTED_002_COMMIT,
            API_CONTAINER_STATE_DIAGNOSTIC_REJECTED_002_TREE,
        ),
        (API_CONTAINER_STATE_DIAGNOSTIC_COMMIT, API_CONTAINER_STATE_DIAGNOSTIC_TREE),
        (ATTEMPT_006_CANDIDATE_COMMIT, ATTEMPT_006_CANDIDATE_TREE),
        (ATTEMPT_006_CLOSURE_COMMIT, ATTEMPT_006_CLOSURE_TREE),
        (
            APPLICATION_STARTUP_STAGE_DIAGNOSTIC_COMMIT,
            APPLICATION_STARTUP_STAGE_DIAGNOSTIC_TREE,
        ),
        (ATTEMPT_007_CANDIDATE_COMMIT, ATTEMPT_007_CANDIDATE_TREE),
        (IMAGE_READABILITY_REPAIR_COMMIT, IMAGE_READABILITY_REPAIR_TREE),
        (ATTEMPT_008_CANDIDATE_COMMIT, ATTEMPT_008_CANDIDATE_TREE),
        (
            ENROLLMENT_OUTPUT_PROJECTION_REPAIR_COMMIT,
            ENROLLMENT_OUTPUT_PROJECTION_REPAIR_TREE,
        ),
    ):
        tree = _git(repo_root, ["show", "-s", "--format=%T", commit], failures)
        if tree != expected_tree:
            failures.append(f"O4 execution bound tree is invalid for {commit}")
        ancestry = subprocess.run(
            ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", commit, "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
        if ancestry.returncode != 0:
            failures.append(f"O4 execution bound commit is not an ancestor: {commit}")
    repair_parents = _git(
        repo_root,
        ["show", "-s", "--format=%P", ENTRYPOINT_REPAIR_COMMIT],
        failures,
    ).split()
    if repair_parents != [ENTRYPOINT_REPAIR_BASE_COMMIT]:
        failures.append("O4 entrypoint repair parent is not exact")
    runtime_native_repair_parents = _git(
        repo_root,
        ["show", "-s", "--format=%P", RUNTIME_NATIVE_REPAIR_COMMIT],
        failures,
    ).split()
    if runtime_native_repair_parents != [IMAGE_RECOVERY_CLOSURE_COMMIT]:
        failures.append("O4 runtime-native repair parent is not exact")
    attempt_004_parents = _git(
        repo_root,
        ["show", "-s", "--format=%P", ATTEMPT_004_CANDIDATE_COMMIT],
        failures,
    ).split()
    if attempt_004_parents != [RUNTIME_NATIVE_REPAIR_COMMIT]:
        failures.append("O4 Attempt 004 candidate parent is not exact")
    attempt_004_closure_parents = _git(
        repo_root,
        ["show", "-s", "--format=%P", ATTEMPT_004_CLOSURE_COMMIT],
        failures,
    ).split()
    if attempt_004_closure_parents != [ATTEMPT_004_CANDIDATE_COMMIT]:
        failures.append("O4 Attempt 004 closure parent is not exact")
    diagnostic_repair_parents = _git(
        repo_root,
        ["show", "-s", "--format=%P", DIAGNOSTIC_REPAIR_COMMIT],
        failures,
    ).split()
    if diagnostic_repair_parents != [ATTEMPT_004_CLOSURE_COMMIT]:
        failures.append("O4 diagnostic repair parent is not exact")
    attempt_005_parents = _git(
        repo_root,
        ["show", "-s", "--format=%P", ATTEMPT_005_CANDIDATE_COMMIT],
        failures,
    ).split()
    if attempt_005_parents != [DIAGNOSTIC_REPAIR_COMMIT]:
        failures.append("O4 Attempt 005 candidate parent is not exact")
    attempt_005_closure_parents = _git(
        repo_root,
        ["show", "-s", "--format=%P", ATTEMPT_005_CLOSURE_COMMIT],
        failures,
    ).split()
    if attempt_005_closure_parents != [ATTEMPT_005_CANDIDATE_COMMIT]:
        failures.append("O4 Attempt 005 closure parent is not exact")
    api_diagnostic_001_parents = _git(
        repo_root,
        ["show", "-s", "--format=%P", API_CONTAINER_STATE_DIAGNOSTIC_REJECTED_001_COMMIT],
        failures,
    ).split()
    if api_diagnostic_001_parents != [ATTEMPT_005_CLOSURE_COMMIT]:
        failures.append("O4 API diagnostic rejected candidate 001 parent is not exact")
    api_diagnostic_002_parents = _git(
        repo_root,
        ["show", "-s", "--format=%P", API_CONTAINER_STATE_DIAGNOSTIC_REJECTED_002_COMMIT],
        failures,
    ).split()
    if api_diagnostic_002_parents != [API_CONTAINER_STATE_DIAGNOSTIC_REJECTED_001_COMMIT]:
        failures.append("O4 API diagnostic rejected candidate 002 parent is not exact")
    api_diagnostic_parents = _git(
        repo_root,
        ["show", "-s", "--format=%P", API_CONTAINER_STATE_DIAGNOSTIC_COMMIT],
        failures,
    ).split()
    if api_diagnostic_parents != [API_CONTAINER_STATE_DIAGNOSTIC_REJECTED_002_COMMIT]:
        failures.append("O4 API diagnostic final candidate parent is not exact")
    attempt_006_parents = _git(
        repo_root,
        ["show", "-s", "--format=%P", ATTEMPT_006_CANDIDATE_COMMIT],
        failures,
    ).split()
    if attempt_006_parents != [API_CONTAINER_STATE_DIAGNOSTIC_COMMIT]:
        failures.append("O4 Attempt 006 candidate parent is not exact")
    attempt_006_closure_parents = _git(
        repo_root,
        ["show", "-s", "--format=%P", ATTEMPT_006_CLOSURE_COMMIT],
        failures,
    ).split()
    if attempt_006_closure_parents != [ATTEMPT_006_CANDIDATE_COMMIT]:
        failures.append("O4 Attempt 006 closure parent is not exact")
    startup_diagnostic_parents = _git(
        repo_root,
        ["show", "-s", "--format=%P", APPLICATION_STARTUP_STAGE_DIAGNOSTIC_COMMIT],
        failures,
    ).split()
    if startup_diagnostic_parents != [ATTEMPT_006_CLOSURE_COMMIT]:
        failures.append("O4 application startup-stage diagnostic parent is not exact")
    attempt_007_parents = _git(
        repo_root,
        ["show", "-s", "--format=%P", ATTEMPT_007_CANDIDATE_COMMIT],
        failures,
    ).split()
    if attempt_007_parents != [APPLICATION_STARTUP_STAGE_DIAGNOSTIC_COMMIT]:
        failures.append("O4 Attempt 007 candidate parent is not exact")
    image_readability_repair_parents = _git(
        repo_root,
        ["show", "-s", "--format=%P", IMAGE_READABILITY_REPAIR_COMMIT],
        failures,
    ).split()
    if image_readability_repair_parents != [IMAGE_READABILITY_REPAIR_BASE_COMMIT]:
        failures.append("O4 image-readability repair parent is not exact")
    attempt_008_parents = _git(
        repo_root,
        ["show", "-s", "--format=%P", ATTEMPT_008_CANDIDATE_COMMIT],
        failures,
    ).split()
    if attempt_008_parents != [IMAGE_READABILITY_REPAIR_COMMIT]:
        failures.append("O4 Attempt 008 candidate parent is not exact")
    enrollment_repair_parents = _git(
        repo_root,
        ["show", "-s", "--format=%P", ENROLLMENT_OUTPUT_PROJECTION_REPAIR_COMMIT],
        failures,
    ).split()
    if enrollment_repair_parents != [ENROLLMENT_OUTPUT_PROJECTION_REPAIR_BASE_COMMIT]:
        failures.append("O4 enrollment-output projection repair parent is not exact")
    runtime_native_changed = _git(
        repo_root,
        [
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            RUNTIME_NATIVE_REPAIR_COMMIT,
        ],
        failures,
    ).splitlines()
    if runtime_native_changed != [
        "deploy/hermes-node-bridge/Dockerfile",
        "scripts/local_v1_lv1_003_o4_producer.py",
        "tests/test_local_v1_lv1_003_o4_producer.py",
        "tests/test_node_fixed_runner_bridge.py",
    ]:
        failures.append("O4 runtime-native repair changed paths are not exact")
    diagnostic_repair_changed = _git(
        repo_root,
        [
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            DIAGNOSTIC_REPAIR_COMMIT,
        ],
        failures,
    ).splitlines()
    if diagnostic_repair_changed != DIAGNOSTIC_REPAIR_PATHS:
        failures.append("O4 diagnostic repair changed paths are not exact")
    attempt_005_changed = _git(
        repo_root,
        [
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            ATTEMPT_005_CANDIDATE_COMMIT,
        ],
        failures,
    ).splitlines()
    if attempt_005_changed != ATTEMPT_005_CONTROL_PATH_ALLOWLIST:
        failures.append("O4 Attempt 005 authorization changed paths are not exact")
    api_diagnostic_changed = _git(
        repo_root,
        [
            "diff",
            "--name-only",
            ATTEMPT_005_CLOSURE_COMMIT,
            API_CONTAINER_STATE_DIAGNOSTIC_COMMIT,
        ],
        failures,
    ).splitlines()
    if api_diagnostic_changed != API_CONTAINER_STATE_DIAGNOSTIC_PATHS:
        failures.append("O4 API container-state diagnostic changed paths are not exact")
    attempt_006_changed = _git(
        repo_root,
        [
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            ATTEMPT_006_CANDIDATE_COMMIT,
        ],
        failures,
    ).splitlines()
    if attempt_006_changed != ATTEMPT_006_CONTROL_PATH_ALLOWLIST:
        failures.append("O4 Attempt 006 authorization changed paths are not exact")
    startup_diagnostic_changed = _git(
        repo_root,
        [
            "diff",
            "--name-only",
            ATTEMPT_006_CLOSURE_COMMIT,
            APPLICATION_STARTUP_STAGE_DIAGNOSTIC_COMMIT,
        ],
        failures,
    ).splitlines()
    if startup_diagnostic_changed != APPLICATION_STARTUP_STAGE_DIAGNOSTIC_PATHS:
        failures.append("O4 application startup-stage diagnostic changed paths are not exact")
    attempt_007_changed = _git(
        repo_root,
        [
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            ATTEMPT_007_CANDIDATE_COMMIT,
        ],
        failures,
    ).splitlines()
    if attempt_007_changed != ATTEMPT_007_CONTROL_PATH_ALLOWLIST:
        failures.append("O4 Attempt 007 authorization changed paths are not exact")
    image_readability_changed = _git(
        repo_root,
        [
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            IMAGE_READABILITY_REPAIR_COMMIT,
        ],
        failures,
    ).splitlines()
    if image_readability_changed != IMAGE_READABILITY_REPAIR_PATHS:
        failures.append("O4 image-readability repair changed paths are not exact")
    for path, expected_digest in IMAGE_READABILITY_REPAIR_PATH_DIGESTS.items():
        contents = _git(
            repo_root,
            ["show", f"{IMAGE_READABILITY_REPAIR_COMMIT}:{path}"],
            failures,
            strip=False,
        )
        if not contents or _digest(contents) != expected_digest:
            failures.append(f"O4 image-readability repair digest is invalid: {path}")
    attempt_008_changed = _git(
        repo_root,
        [
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            ATTEMPT_008_CANDIDATE_COMMIT,
        ],
        failures,
    ).splitlines()
    if attempt_008_changed != ATTEMPT_008_CONTROL_PATH_ALLOWLIST:
        failures.append("O4 Attempt 008 authorization changed paths are not exact")
    enrollment_repair_changed = _git(
        repo_root,
        [
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            ENROLLMENT_OUTPUT_PROJECTION_REPAIR_COMMIT,
        ],
        failures,
    ).splitlines()
    if enrollment_repair_changed != ENROLLMENT_OUTPUT_PROJECTION_REPAIR_PATHS:
        failures.append("O4 enrollment-output projection repair changed paths are not exact")
    for path, expected_digest in ENROLLMENT_OUTPUT_PROJECTION_REPAIR_PATH_DIGESTS.items():
        contents = _git(
            repo_root,
            ["show", f"{ENROLLMENT_OUTPUT_PROJECTION_REPAIR_COMMIT}:{path}"],
            failures,
            strip=False,
        )
        if not contents or _digest(contents) != expected_digest:
            failures.append(f"O4 enrollment-output projection repair digest is invalid: {path}")
    historical = _git(
        repo_root,
        [
            "show",
            f"{CODE_AUTHORIZATION_ORIGIN_COMMIT}:{code_authorization.AUTHORIZATION}",
        ],
        failures,
        strip=False,
    )
    if historical and _digest(historical) != CODE_AUTHORIZATION_ORIGIN_RECORD_DIGEST:
        failures.append("O4 execution code authorization origin record digest is invalid")
    current_historical = _git(
        repo_root,
        [
            "show",
            f"{CODE_AUTHORIZATION_COMMIT}:{code_authorization.AUTHORIZATION}",
        ],
        failures,
        strip=False,
    )
    if current_historical and _digest(current_historical) != CODE_AUTHORIZATION_RECORD_DIGEST:
        failures.append("O4 execution bound code authorization record digest is invalid")
    current_authorization = _file_digest(
        repo_root / code_authorization.AUTHORIZATION,
        failures,
    )
    if current_authorization != CODE_AUTHORIZATION_RECORD_DIGEST:
        failures.append("O4 execution current code authorization record digest is invalid")


def _validate_attempted_candidate_binding(
    repo_root: Path,
    failures: list[str],
) -> None:
    tree = _git(
        repo_root,
        ["show", "-s", "--format=%T", ATTEMPT_001_CANDIDATE_COMMIT],
        failures,
    )
    if tree != ATTEMPT_001_CANDIDATE_TREE:
        failures.append("O4 Attempt 001 candidate tree is invalid")
    ancestry = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "merge-base",
            "--is-ancestor",
            ATTEMPT_001_CANDIDATE_COMMIT,
            "HEAD",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if ancestry.returncode != 0:
        failures.append("O4 Attempt 001 candidate is not an ancestor of the closure")
    historical_contract = _git(
        repo_root,
        ["show", f"{ATTEMPT_001_CANDIDATE_COMMIT}:{CONTRACT.as_posix()}"],
        failures,
        strip=False,
    )
    if (
        historical_contract
        and _digest(historical_contract) != ATTEMPT_001_AUTHORIZATION_CONTRACT_DIGEST
    ):
        failures.append("O4 Attempt 001 authorization contract digest is invalid")


def _validate_attempt_002_candidate_binding(
    repo_root: Path,
    failures: list[str],
) -> None:
    tree = _git(
        repo_root,
        ["show", "-s", "--format=%T", ATTEMPT_002_CANDIDATE_COMMIT],
        failures,
    )
    if tree != ATTEMPT_002_CANDIDATE_TREE:
        failures.append("O4 Attempt 002 candidate tree is invalid")
    ancestry = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "merge-base",
            "--is-ancestor",
            ATTEMPT_002_CANDIDATE_COMMIT,
            "HEAD",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if ancestry.returncode != 0:
        failures.append("O4 Attempt 002 candidate is not an ancestor of the closure")


def _validate_attempt_003_candidate_binding(
    repo_root: Path,
    failures: list[str],
) -> None:
    tree = _git(
        repo_root,
        ["show", "-s", "--format=%T", ATTEMPT_003_CANDIDATE_COMMIT],
        failures,
    )
    if tree != ATTEMPT_003_CANDIDATE_TREE:
        failures.append("O4 Attempt 003 candidate tree is invalid")
    ancestry = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "merge-base",
            "--is-ancestor",
            ATTEMPT_003_CANDIDATE_COMMIT,
            "HEAD",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if ancestry.returncode != 0:
        failures.append("O4 Attempt 003 candidate is not an ancestor of the closure")


def _validate_recorded_root_absence(
    repo_root: Path,
    failures: list[str],
) -> None:
    for relative in PRIOR_ATTEMPT_ROOTS:
        try:
            (repo_root / relative).lstat()
        except FileNotFoundError:
            continue
        except OSError:
            failures.append(f"O4 Attempt 001 observed root posture is unreadable: {relative}")
            continue
        failures.append(f"O4 Attempt 001 observed-absent root is now present: {relative}")


def _validate_source_bindings(
    repo_root: Path,
    contract: JsonObject,
    failures: list[str],
) -> None:
    producer_digest = _file_digest(repo_root / PRODUCER_CONTRACT, failures)
    if producer_digest != PRODUCER_CONTRACT_DIGEST:
        failures.append("O4 execution current producer contract digest is invalid")
    if not _exact_json_equal(
        contract.get("producer_contract_sha256"),
        producer_digest,
    ):
        failures.append("O4 execution producer contract source binding is invalid")
    profile = contract.get("profile")
    if not isinstance(profile, dict):
        return
    for key, (path, expected) in SOURCE_DIGESTS.items():
        if _file_digest(repo_root / path, failures) != expected:
            failures.append(f"O4 execution current source differs for {key}")
    for relative, expected_digest in ENROLLMENT_OUTPUT_PROJECTION_REPAIR_PATH_DIGESTS.items():
        repair_expected_digest = cast(str, expected_digest)
        if _file_digest(repo_root / relative, failures) != repair_expected_digest:
            failures.append(f"O4 enrollment-output projection repair differs for {relative}")
    try:
        raw_profile = json.loads(
            (repo_root / "deploy/hermes-node-bridge/profile.json").read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicates,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        failures.append("O4 execution profile cannot be canonicalized")
        return
    if not isinstance(raw_profile, dict) or sha256_digest(cast(JsonObject, raw_profile)) != (
        PROFILE_DIGEST
    ):
        failures.append("O4 execution current canonical profile digest is invalid")


def _validate_current_license_discovery(
    repo_root: Path,
    failures: list[str],
) -> None:
    tracked_output = _git(
        repo_root,
        ["ls-tree", "-r", "--name-only", "HEAD"],
        failures,
    )
    if not tracked_output:
        failures.append("O4 execution tracked Git tree inventory is unavailable")
        return
    tracked_paths = tracked_output.splitlines()
    license_family_files = sorted(
        path
        for path in tracked_paths
        if Path(path).name.startswith(("LICENSE", "NOTICE", "COPYING"))
    )
    inventory_inputs = sorted(
        path for path in tracked_paths if path in {"pyproject.toml", "uv.lock"}
    )
    if inventory_inputs != ["pyproject.toml", "uv.lock"]:
        failures.append("O4 execution current license inventory inputs are not exact")
    if license_family_files:
        failures.append("O4 execution current tracked license-family files are not empty")
    for relative in inventory_inputs:
        path = repo_root / relative
        try:
            metadata = path.lstat()
        except OSError:
            failures.append(f"O4 execution license input is unavailable: {relative}")
            continue
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            failures.append(f"O4 execution license input is not a no-follow file: {relative}")
        if metadata.st_size > 1048576:
            failures.append(f"O4 execution license input exceeds size ceiling: {relative}")


def _read_contract(path: Path, failures: list[str]) -> JsonObject:
    try:
        document = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicates,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        failures.append("O4 execution authorization JSON is unavailable or ambiguous")
        return {}
    if not isinstance(document, dict):
        failures.append("O4 execution authorization JSON is not an object")
        return {}
    return cast(JsonObject, document)


def _exact_json_equal(actual: object, expected: object) -> bool:
    """Compare closed JSON values without Python's bool/int coercion."""
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or actual.keys() != expected.keys():
            return False
        return all(
            _exact_json_equal(actual[key], expected_value)
            for key, expected_value in expected.items()
        )
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return False
        return all(
            _exact_json_equal(actual_value, expected_value)
            for actual_value, expected_value in zip(actual, expected, strict=True)
        )
    return actual == expected


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError(f"duplicate key: {key}")
        document[key] = value
    return document


def _read_text(path: Path, failures: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        failures.append(f"O4 execution authorization input is unavailable: {path}")
        return ""


def _file_digest(path: Path, failures: list[str]) -> str:
    try:
        return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        failures.append(f"O4 execution source is unavailable: {path}")
        return ""


def _digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def _git(
    repo_root: Path,
    arguments: list[str],
    failures: list[str],
    *,
    strip: bool = True,
) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        failures.append(f"O4 execution git command failed: {' '.join(arguments)}")
        return ""
    return result.stdout.rstrip("\n") if strip else result.stdout


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "LV1-003 O4 execution authorization check",
        f"valid: {str(report['valid']).lower()}",
        f"record_status: {report['record_status']}",
        f"attempt_id: {report['attempt_id']}",
        f"attempt_consumed: {str(report['attempt_consumed']).lower()}",
        f"retry_authorized: {str(report['retry_authorized']).lower()}",
        f"execution_attempt_budget: {report['execution_attempt_budget']}",
        f"live_execution_authorized: {str(report['live_execution_authorized']).lower()}",
        f"docker_lifecycle_authorized: {str(report['docker_lifecycle_authorized']).lower()}",
        f"provider_access_authorized: {str(report['provider_access_authorized']).lower()}",
        "o4_evidence_execution_authorized: "
        f"{str(report['o4_evidence_execution_authorized']).lower()}",
        f"new_governed_tool: {str(report['new_governed_tool']).lower()}",
        f"release_allowed: {str(report['release_allowed']).lower()}",
        f"uat_complete: {str(report['uat_complete']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def main() -> int:
    report = build_report(ROOT)
    print(render_report(report))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
