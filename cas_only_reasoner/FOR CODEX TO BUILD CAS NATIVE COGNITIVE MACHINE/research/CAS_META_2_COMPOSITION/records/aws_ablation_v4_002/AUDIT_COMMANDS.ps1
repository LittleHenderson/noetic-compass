# Run from research/CAS_META_2_COMPOSITION. Outputs must not already exist.
# These commands inspect evidence only; they do not load neural checkpoints.
& C:/Python314/python.exe -B -m tools.inspect_ablation_packet_v5 --packet records/aws_ablation_v4_002/cloud_artifacts.zip --sha256 c0fbc413ce94a3b192a5b634bfc246dae96d94f3fe01943caacbff83a4e74708 --source-archive records/aws_ablation_v4_source_002/source.zip --source-sha256 3230d805b665b91f1191d423342bb591cfb1fd69cd677fbe49206cf50b8729bd --source-sha 9f562c761c7cb84c767673b2fab735cdd031b499 --job cas-meta2-20260906032109-361b34a0 --output records/aws_ablation_v4_inspection_002 --extract records/aws_ablation_v4_002_extracted
if ($LASTEXITCODE -ne 0) { throw 'Packet inspection failed' }
$receiptHash = (Get-FileHash -LiteralPath 'records/aws_ablation_v4_inspection_002/inspection_receipt.json' -Algorithm SHA256).Hash.ToLower()
& C:/Python314/python.exe -B -m tools.audit_ablation_stored_v4 --inspection records/aws_ablation_v4_inspection_002/inspection_receipt.json --inspection-sha256 $receiptHash --source-archive records/aws_ablation_v4_source_002/source.zip --source-sha256 3230d805b665b91f1191d423342bb591cfb1fd69cd677fbe49206cf50b8729bd --source-sha 9f562c761c7cb84c767673b2fab735cdd031b499 --job cas-meta2-20260906032109-361b34a0 --packet-sha256 c0fbc413ce94a3b192a5b634bfc246dae96d94f3fe01943caacbff83a4e74708 --output records/aws_ablation_v4_stored_audit_002
if ($LASTEXITCODE -ne 0) { throw 'Stored outcome audit failed' }
# Provider check requires the existing signed-in AWS profile.
& C:/Python314/python.exe -B records/aws_ablation_v4_002/check_cleanup.py
