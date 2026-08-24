# Explainability Feature Map

Schema: `network-state-v1.0`  
Input: `data/processed/cic_ids2018_network_states.parquet`  
Aggregation interval: **10 seconds**

These are model-input features, not causal variables. Their interpretation is limited to how the trained model responds when a standardized input value is ablated. The state table contains flow-derived aggregates; packet-accurate interpretations remain outside the frozen V1 contract.

| Feature | Meaning | Unit | State aggregation | Expected interpretation | Higher values generally indicate | Limitations |
|---|---|---|---|---|---|---|
| `flow_count` | Number of valid flows | flows | Count rows in the 10-second state | Activity volume | More observed flow activity | Does not identify hosts or attack cause |
| `byte_sum` | Total forward and backward bytes | source bytes | Sum directional byte fields | Traffic volume | More transferred bytes | Directional and payload details are compressed |
| `packet_sum` | Total forward and backward packets | packets | Sum directional packet counts | Packet activity volume | More packets | Not packet-level timing or payload evidence |
| `mean_duration` | Mean flow duration | source export units | Mean of flow durations | Typical connection lifetime | Longer-lived flows | Source unit is retained without reinterpretation |
| `median_duration` | Median flow duration | source export units | Median of flow durations | Typical central flow lifetime | Longer central duration | Hides tail behavior and individual flow identity |
| `mean_iat` | Mean of flow-level inter-arrival-time means | source export units | Mean of `Flow IAT Mean` | Average flow timing separation | Larger reported IAT | Not a packet-order IAT measurement |
| `iat_std` | Mean of flow-level IAT standard deviations | source export units | Mean of `Flow IAT Std` | Within-flow timing variability proxy | More timing variability | Aggregates already summarized flow statistics |
| `syn_flow_ratio` | Fraction of flows with a SYN flag count | proportion | Flows where `SYN Flag Cnt > 0` divided by flow count | Connection-establishment behavior | More SYN-bearing flows | Does not preserve flag order or packet context |
| `ack_flow_ratio` | Fraction of flows with an ACK flag count | proportion | Flows where `ACK Flag Cnt > 0` divided by flow count | Acknowledgement presence | More ACK-bearing flows | Not a complete handshake or TCP-state history |
| `rst_flow_ratio` | Fraction of flows with an RST flag count | proportion | Flows where `RST Flag Cnt > 0` divided by flow count | Reset-related behavior | More reset-bearing flows | Cannot distinguish benign resets from attack behavior |
| `fwd_byte_share` | Forward bytes as a share of total bytes | proportion | Forward bytes divided by total bytes; zero if total is zero | Directional byte balance | More forward-dominant traffic | No source/destination identity is retained |
| `fwd_packet_share` | Forward packets as a share of total packets | proportion | Forward packets divided by total packets; zero if total is zero | Directional packet balance | More forward-dominant packet activity | Does not reveal packet sequence or endpoint role |
| `unique_destination_port_count` | Number of distinct destination ports | ports | Count distinct `Dst Port` values in the state | Port fan-out/diversity | More destination-port diversity | Destination-port diversity is not host fan-out |
| `bytes_per_second` | Byte throughput proxy | bytes/second | `byte_sum / 10` | Rate of transferred bytes | Higher byte rate | A state rate, not a continuous link measurement |
| `packets_per_second` | Packet throughput proxy | packets/second | `packet_sum / 10` | Rate of packet activity | Higher packet rate | Does not contain packet-level burst structure |
| `packet_size_mean` | Mean flow-level packet-length mean | source export units | Mean of `Pkt Len Mean` | Typical packet-size proxy | Larger average packet size | Not a raw packet-size distribution |
| `packet_size_std` | Mean flow-level packet-length standard deviation | source export units | Mean of `Pkt Len Std` | Packet-size variability proxy | More size variability | Does not preserve payload or packet-order detail |

## Attribution interpretation

The explainability reports use deterministic masking in the model's standardized input space: one feature or temporal position is replaced with the training-fitted scaler mean (approximately zero), then the frozen checkpoint is run again. A positive contribution means the original input produced a higher model score than its masked counterpart for that forecast step. This is model sensitivity, not causal evidence.

Temporal positions for L=10 are labeled `t-90s`, `t-80s`, ..., `t-10s`, `t`, where `t` is the final state in the input sequence. No future target rows are used to construct explanations.
