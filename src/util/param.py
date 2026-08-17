from . import *

# 定位标识符
P1 = "1-GPS"
P2 = "2-DGPS"
P4 = "4-Fixed"
P5 = "5-Float"
P6 = "6-DR"

time_list = [
    "Start time(UTC)",
    "End time(UTC)",
    "Test duration(hours)",
]


position_index_list = time_list + [
    "Frequency",
    "PDOP Avg",
    "HDOP Avg",
    "VDOP Avg",
]
position_index_list.append("Parsed Satellites Avg")
for cep in cep_list:
    position_index_list.append(f"Parsed Satellites {cep}")

for cep in cep_list:
    position_index_list.append(f"Visibled Satellites {cep}")

position_index_list.append("")
position_index_list.append("All CN0 Avg")
for cep in cep_list:
    position_index_list.append(f"All CN0 {cep}")

for cep in cep_list:
    position_index_list.append(f"Top{{}} CN0 {cep}")

position_index_list.extend(
    [
        "GPS Avg(L1+L2+L5)",
        "BDS Avg(B1I+B2A+B2B)",
        "BDS Avg(B1C+B2I+B3I)",
        "GAL Avg(E1+E5A+E5B+E6)",
        "GLO Avg(G1+G2)",
        "QZSS Avg(Q1+Q2+Q5)",
        "IRNSS Avg(I5)",
        "Total rate",
        "0-Unfixed rate",
        f"{P1} rate",
        f"{P2} rate",
        "3-PPS rate",
        f"{P4} rate",
        f"{P5} rate",
        f"{P6} rate",
        "7-Input rate",
        "Fixed availability",
        "0-Heading rate",
        "4-Heading rate",
        "5-Heading rate",
        "Mis-Seconds",
        "Integrity of NMEA",
        "ChecksumError Count",
        "",
        "Accuracy Result:",
    ]
)


for cep in rms_sigma_cep_list:
    position_index_list.append(f"{HA} {cep}(m)")

for cep in rms_sigma_cep_list:
    position_index_list.append(f"{VA} {cep}(m)")


for cep in rms_cep_list:
    position_index_list.append(f"SOG {cep}(m/s)")

for cep in rms_cep_list:
    position_index_list.append(f"COG {cep}(°)")

position_index_list.extend(["", "PQTMVEL Result:"])
for cep in rms_sigma_cep_list:
    position_index_list.append(f"Heading {cep}(°)")
position_index_list.append("Confidence Coefficient")
for cep in rms_sigma_cep_list:
    position_index_list.append(f"2D Velocity {cep}(m/s)")
position_index_list.append("Confidence Coefficient")
for cep in rms_sigma_cep_list:
    position_index_list.append(f"3D Velocity {cep}(m/s)")
position_index_list.append("Confidence Coefficient")
for cep in cep_list:
    position_index_list.append(f"VEL-N {cep}(m/s)")
for cep in cep_list:
    position_index_list.append(f"VEL-E {cep}(m/s)")
for cep in cep_list:
    position_index_list.append(f"VEL-D {cep}(m/s)")

position_index_list.extend(["", "Roll/Pitch/Heading Result:"])
for cep in rms_sigma_cep_list:
    position_index_list.append(f"Roll {cep} From AVG(°)")
for cep in rms_sigma_cep_list:
    position_index_list.append(f"Pitch {cep} From AVG(°)")
for cep in rms_sigma_cep_list:
    position_index_list.append(f"Heading {cep} From AVG(°)")
for cep in rms_sigma_cep_list:
    position_index_list.append(f"Roll {cep} From RMS(°)")
for cep in rms_sigma_cep_list:
    position_index_list.append(f"Pitch {cep} From RMS(°)")
for cep in rms_sigma_cep_list:
    position_index_list.append(f"Heading {cep} From RMS(°)")

position_index_list.extend(["", f"{P1} Accuracy:"])
for cep in rms_cep_list:
    position_index_list.append(f"{P1} Positional {cep}(m)")
for cep in rms_cep_list:
    position_index_list.append(f"{P1} Altitude {cep}(m)")

position_index_list.extend(["", f"{P2} Accuracy:"])
for cep in rms_cep_list:
    position_index_list.append(f"{P2} Positional {cep}(m)")
for cep in rms_cep_list:
    position_index_list.append(f"{P2} Altitude {cep}(m)")

position_index_list.extend(["", f"{P4} Accuracy:"])
for cep in rms_cep_list:
    position_index_list.append(f"{P4} Positional {cep}(m)")
for cep in rms_cep_list:
    position_index_list.append(f"{P4} Altitude {cep}(m)")


position_index_list.extend(["", f"{P5} Accuracy:"])
for cep in rms_cep_list:
    position_index_list.append(f"{P5} Positional {cep}(m)")
for cep in rms_cep_list:
    position_index_list.append(f"{P5} Altitude {cep}(m)")

position_index_list.extend(["", f"{P6} Accuracy:"])
for cep in rms_cep_list:
    position_index_list.append(f"{P6} Positional {cep}(m)")
for cep in rms_cep_list:
    position_index_list.append(f"{P6} Altitude {cep}(m)")

pps_index_list = [
    "MEAN:",
    "RMS:",
    "CEP50:",
    "CEP68:",
    "CEP95:",
    "CEP99:",
]

parameters = {"coordinates": {}, "error_list": [], "header_list": []}
