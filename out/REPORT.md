# Tool report card: which tools agents get wrong, and how

Source: tau2-bench published results (Sierra Research), 4 models, airline + retail. Every write-tool call is compared with the task's
ground-truth actions. No LLM judge. Rates are per required call, with 95% Wilson intervals. Trials repeat the same
tasks, so intervals are optimistic.

## Does the grader agree with the benchmark's own check?

| model | domain | episodes | benchmark says correct, we flag a write error | benchmark says wrong, explained by a write error |
|---|---|---|---|---|
| claude-3-7-sonnet-20250219 | airline | 200 | 0/102 | 98/98 (100%) |
| claude-3-7-sonnet-20250219 | retail | 456 | 14/365 | 91/91 (100%) |
| gpt-4.1-2025-04-14 | airline | 200 | 0/116 | 84/84 (100%) |
| gpt-4.1-2025-04-14 | retail | 456 | 15/354 | 102/102 (100%) |
| gpt-4.1-mini-2025-04-14 | airline | 200 | 2/111 | 89/89 (100%) |
| gpt-4.1-mini-2025-04-14 | retail | 456 | 14/330 | 126/126 (100%) |
| o4-mini-2025-04-16 | airline | 200 | 5/119 | 81/81 (100%) |
| o4-mini-2025-04-16 | retail | 456 | 15/338 | 118/118 (100%) |

Failures not explained by a write error are wrong answers to questions (tau-bench's output check) or
tasks where the right move was no write at all.

## Per tool

| tool | model | required | correct | wrong args | wrong tool | handed off | missed | most common reason |
|---|---|---|---|---|---|---|---|---|
| `return_delivered_order_items` | claude-3-7-sonnet-20250219 | 172 | 90% (84-93) | 7 | 1 | 2 | 8 | missed (8) |
| `return_delivered_order_items` | gpt-4.1-2025-04-14 | 172 | 87% (81-91) | 5 | 1 | 4 | 13 | missed (13) |
| `return_delivered_order_items` | gpt-4.1-mini-2025-04-14 | 172 | 86% (80-90) | 3 | 1 | 6 | 14 | missed (14) |
| `return_delivered_order_items` | o4-mini-2025-04-16 | 172 | 82% (76-87) | 10 | 1 | 11 | 9 | handed off: transferred to human (11) |
| `modify_pending_order_items` | claude-3-7-sonnet-20250219 | 156 | 87% (80-91) | 16 | 4 | 0 | 1 | wrong args: new_item_ids (7) |
| `modify_pending_order_items` | gpt-4.1-2025-04-14 | 156 | 74% (66-80) | 21 | 4 | 2 | 14 | missed (14) |
| `modify_pending_order_items` | gpt-4.1-mini-2025-04-14 | 156 | 59% (51-66) | 27 | 5 | 1 | 31 | missed (31) |
| `modify_pending_order_items` | o4-mini-2025-04-16 | 156 | 79% (72-85) | 24 | 0 | 1 | 8 | missed (8) |
| `exchange_delivered_order_items` | claude-3-7-sonnet-20250219 | 140 | 81% (73-86) | 20 | 2 | 1 | 4 | wrong args: new_item_ids (11) |
| `exchange_delivered_order_items` | gpt-4.1-2025-04-14 | 140 | 79% (71-85) | 11 | 9 | 1 | 9 | missed (9) |
| `exchange_delivered_order_items` | gpt-4.1-mini-2025-04-14 | 140 | 71% (63-78) | 18 | 3 | 1 | 18 | missed (18) |
| `exchange_delivered_order_items` | o4-mini-2025-04-16 | 140 | 70% (62-77) | 28 | 3 | 2 | 9 | wrong args: new_item_ids (12) |
| `cancel_pending_order` | claude-3-7-sonnet-20250219 | 100 | 89% (81-94) | 7 | 0 | 1 | 3 | wrong args: reason (5) |
| `cancel_pending_order` | gpt-4.1-2025-04-14 | 100 | 93% (86-97) | 7 | 0 | 0 | 0 | wrong args: reason (4) |
| `cancel_pending_order` | gpt-4.1-mini-2025-04-14 | 100 | 91% (84-95) | 4 | 1 | 1 | 3 | wrong args: reason (3) |
| `cancel_pending_order` | o4-mini-2025-04-16 | 100 | 79% (70-86) | 9 | 0 | 5 | 7 | missed (7) |
| `modify_pending_order_address` | claude-3-7-sonnet-20250219 | 96 | 84% (76-90) | 5 | 3 | 0 | 7 | missed (7) |
| `modify_pending_order_address` | gpt-4.1-2025-04-14 | 96 | 77% (68-84) | 5 | 3 | 1 | 13 | missed (13) |
| `modify_pending_order_address` | gpt-4.1-mini-2025-04-14 | 96 | 72% (62-80) | 6 | 2 | 0 | 19 | missed (19) |
| `modify_pending_order_address` | o4-mini-2025-04-16 | 96 | 69% (59-77) | 5 | 0 | 5 | 20 | missed (20) |
| `update_reservation_flights` | claude-3-7-sonnet-20250219 | 84 | 73% (62-81) | 12 | 1 | 1 | 9 | missed (9) |
| `update_reservation_flights` | gpt-4.1-2025-04-14 | 84 | 71% (61-80) | 4 | 1 | 2 | 17 | missed (17) |
| `update_reservation_flights` | gpt-4.1-mini-2025-04-14 | 84 | 73% (62-81) | 11 | 0 | 0 | 12 | missed (12) |
| `update_reservation_flights` | o4-mini-2025-04-16 | 84 | 56% (45-66) | 6 | 5 | 10 | 16 | missed (16) |
| `cancel_reservation` | claude-3-7-sonnet-20250219 | 52 | 75% (62-85) | 5 | 6 | 0 | 2 | wrong tool: called update_reservation_flights (6) |
| `cancel_reservation` | gpt-4.1-2025-04-14 | 52 | 73% (60-83) | 5 | 1 | 0 | 8 | missed (8) |
| `cancel_reservation` | gpt-4.1-mini-2025-04-14 | 52 | 85% (72-92) | 1 | 2 | 0 | 5 | missed (5) |
| `cancel_reservation` | o4-mini-2025-04-16 | 52 | 46% (33-59) | 1 | 1 | 16 | 10 | handed off: transferred to human (16) |
| `modify_user_address` | claude-3-7-sonnet-20250219 | 44 | 84% (71-92) | 2 | 0 | 0 | 5 | missed (5) |
| `modify_user_address` | gpt-4.1-2025-04-14 | 44 | 91% (79-96) | 3 | 0 | 0 | 1 | wrong args: address1,address2,zip (2) |
| `modify_user_address` | gpt-4.1-mini-2025-04-14 | 44 | 91% (79-96) | 3 | 0 | 0 | 1 | wrong args: address1,address2,zip (3) |
| `modify_user_address` | o4-mini-2025-04-16 | 44 | 66% (51-78) | 4 | 0 | 4 | 7 | missed (7) |
| `book_reservation` | claude-3-7-sonnet-20250219 | 36 | 42% (27-58) | 8 | 3 | 3 | 7 | missed (7) |
| `book_reservation` | gpt-4.1-2025-04-14 | 36 | 31% (18-47) | 15 | 0 | 0 | 10 | missed (10) |
| `book_reservation` | gpt-4.1-mini-2025-04-14 | 36 | 33% (20-50) | 14 | 0 | 0 | 10 | missed (10) |
| `book_reservation` | o4-mini-2025-04-16 | 36 | 28% (16-44) | 15 | 0 | 4 | 7 | missed (7) |
| `update_reservation_baggages` | claude-3-7-sonnet-20250219 | 24 | 54% (35-72) | 6 | 0 | 1 | 4 | missed (4) |
| `update_reservation_baggages` | gpt-4.1-2025-04-14 | 24 | 29% (15-49) | 11 | 2 | 0 | 4 | wrong args: nonfree_baggages (8) |
| `update_reservation_baggages` | gpt-4.1-mini-2025-04-14 | 24 | 33% (18-53) | 12 | 0 | 0 | 4 | wrong args: nonfree_baggages (11) |
| `update_reservation_baggages` | o4-mini-2025-04-16 | 24 | 29% (15-49) | 12 | 0 | 2 | 3 | wrong args: payment_id (6) |
| `update_reservation_passengers` | claude-3-7-sonnet-20250219 | 12 | 75% (47-91) | 0 | 0 | 0 | 3 | missed (3) |
| `update_reservation_passengers` | gpt-4.1-2025-04-14 | 12 | 67% (39-86) | 0 | 0 | 0 | 4 | missed (4) |
| `update_reservation_passengers` | gpt-4.1-mini-2025-04-14 | 12 | 75% (47-91) | 1 | 0 | 0 | 2 | missed (2) |
| `update_reservation_passengers` | o4-mini-2025-04-16 | 12 | 75% (47-91) | 1 | 0 | 1 | 1 | handed off: transferred to human (1) |
| `send_certificate` | claude-3-7-sonnet-20250219 | 12 | 67% (39-86) | 0 | 0 | 4 | 0 | handed off: transferred to human (4) |
| `send_certificate` | gpt-4.1-2025-04-14 | 12 | 25% (9-53) | 3 | 0 | 2 | 4 | missed (4) |
| `send_certificate` | gpt-4.1-mini-2025-04-14 | 12 | 83% (55-95) | 1 | 0 | 1 | 0 | wrong args: amount (1) |
| `send_certificate` | o4-mini-2025-04-16 | 12 | 33% (14-61) | 2 | 0 | 5 | 1 | handed off: transferred to human (5) |
| `modify_pending_order_payment` | claude-3-7-sonnet-20250219 | 4 | 100% (51-100) | 0 | 0 | 0 | 0 | - |
| `modify_pending_order_payment` | gpt-4.1-2025-04-14 | 4 | 100% (51-100) | 0 | 0 | 0 | 0 | - |
| `modify_pending_order_payment` | gpt-4.1-mini-2025-04-14 | 4 | 100% (51-100) | 0 | 0 | 0 | 0 | - |
| `modify_pending_order_payment` | o4-mini-2025-04-16 | 4 | 100% (51-100) | 0 | 0 | 0 | 0 | - |

## When the arguments were wrong, which argument?

| tool | model | argument | times |
|---|---|---|---|
| `modify_pending_order_items` | gpt-4.1-mini-2025-04-14 | `new_item_ids` | 19 |
| `exchange_delivered_order_items` | claude-3-7-sonnet-20250219 | `new_item_ids` | 18 |
| `exchange_delivered_order_items` | o4-mini-2025-04-16 | `new_item_ids` | 17 |
| `modify_pending_order_items` | gpt-4.1-2025-04-14 | `new_item_ids` | 14 |
| `update_reservation_baggages` | gpt-4.1-mini-2025-04-14 | `nonfree_baggages` | 12 |
| `exchange_delivered_order_items` | gpt-4.1-mini-2025-04-14 | `new_item_ids` | 12 |
| `update_reservation_flights` | claude-3-7-sonnet-20250219 | `flights` | 10 |
| `update_reservation_baggages` | gpt-4.1-2025-04-14 | `nonfree_baggages` | 10 |
| `book_reservation` | gpt-4.1-mini-2025-04-14 | `payment_methods` | 10 |
| `modify_pending_order_items` | claude-3-7-sonnet-20250219 | `new_item_ids` | 10 |
| `return_delivered_order_items` | o4-mini-2025-04-16 | `item_ids` | 10 |
| `book_reservation` | gpt-4.1-2025-04-14 | `payment_methods` | 9 |
| `update_reservation_flights` | gpt-4.1-mini-2025-04-14 | `flights` | 9 |
| `book_reservation` | gpt-4.1-mini-2025-04-14 | `passengers` | 9 |
| `book_reservation` | o4-mini-2025-04-16 | `passengers` | 9 |

## Writes nobody asked for (and writes the tool refused)

| tool | model | unwanted | duplicate | refused by tool |
|---|---|---|---|---|
| `cancel_reservation` | gpt-4.1-mini-2025-04-14 | 55 | 0 | 0 |
| `cancel_reservation` | claude-3-7-sonnet-20250219 | 50 | 0 | 0 |
| `cancel_reservation` | gpt-4.1-2025-04-14 | 26 | 0 | 0 |
| `update_reservation_flights` | claude-3-7-sonnet-20250219 | 16 | 0 | 24 |
| `cancel_pending_order` | claude-3-7-sonnet-20250219 | 13 | 0 | 1 |
| `update_reservation_flights` | gpt-4.1-mini-2025-04-14 | 12 | 1 | 20 |
| `cancel_reservation` | o4-mini-2025-04-16 | 12 | 0 | 0 |
| `cancel_pending_order` | gpt-4.1-2025-04-14 | 10 | 0 | 0 |
| `send_certificate` | claude-3-7-sonnet-20250219 | 9 | 0 | 0 |
| `cancel_pending_order` | gpt-4.1-mini-2025-04-14 | 9 | 0 | 0 |
| `return_delivered_order_items` | claude-3-7-sonnet-20250219 | 8 | 0 | 19 |
| `send_certificate` | gpt-4.1-2025-04-14 | 5 | 0 | 1 |
| `return_delivered_order_items` | o4-mini-2025-04-16 | 5 | 0 | 11 |
| `update_reservation_flights` | gpt-4.1-2025-04-14 | 4 | 0 | 10 |
| `modify_user_address` | gpt-4.1-2025-04-14 | 1 | 3 | 0 |
| `return_delivered_order_items` | gpt-4.1-2025-04-14 | 4 | 0 | 8 |
| `update_reservation_baggages` | gpt-4.1-mini-2025-04-14 | 1 | 2 | 10 |
| `book_reservation` | claude-3-7-sonnet-20250219 | 3 | 0 | 3 |
| `update_reservation_flights` | o4-mini-2025-04-16 | 3 | 0 | 5 |
| `book_reservation` | o4-mini-2025-04-16 | 3 | 0 | 4 |
| `modify_pending_order_address` | claude-3-7-sonnet-20250219 | 2 | 0 | 0 |
| `exchange_delivered_order_items` | claude-3-7-sonnet-20250219 | 2 | 0 | 13 |
| `send_certificate` | o4-mini-2025-04-16 | 2 | 0 | 0 |
| `book_reservation` | gpt-4.1-mini-2025-04-14 | 2 | 0 | 30 |
| `return_delivered_order_items` | gpt-4.1-mini-2025-04-14 | 2 | 0 | 31 |
| `modify_pending_order_address` | gpt-4.1-mini-2025-04-14 | 0 | 1 | 2 |
| `modify_pending_order_address` | o4-mini-2025-04-16 | 1 | 0 | 1 |
| `exchange_delivered_order_items` | gpt-4.1-2025-04-14 | 1 | 0 | 24 |
| `exchange_delivered_order_items` | gpt-4.1-mini-2025-04-14 | 1 | 0 | 64 |
| `update_reservation_baggages` | o4-mini-2025-04-16 | 1 | 0 | 0 |
| `cancel_pending_order` | o4-mini-2025-04-16 | 1 | 0 | 0 |
| `book_reservation` | gpt-4.1-2025-04-14 | 1 | 0 | 2 |
| `modify_user_address` | gpt-4.1-mini-2025-04-14 | 0 | 1 | 0 |
| `update_reservation_baggages` | claude-3-7-sonnet-20250219 | 1 | 0 | 0 |
| `modify_pending_order_items` | claude-3-7-sonnet-20250219 | 0 | 0 | 18 |
| `update_reservation_passengers` | gpt-4.1-mini-2025-04-14 | 0 | 0 | 1 |
| `exchange_delivered_order_items` | o4-mini-2025-04-16 | 0 | 0 | 12 |
| `update_reservation_baggages` | gpt-4.1-2025-04-14 | 0 | 0 | 4 |
| `modify_pending_order_payment` | gpt-4.1-mini-2025-04-14 | 0 | 0 | 2 |
| `modify_pending_order_items` | gpt-4.1-mini-2025-04-14 | 0 | 0 | 35 |
| `modify_pending_order_items` | gpt-4.1-2025-04-14 | 0 | 0 | 38 |
| `modify_pending_order_items` | o4-mini-2025-04-16 | 0 | 0 | 1 |

## Errors the tools returned

| tool | model | error | times |
|---|---|---|---|
| `get_order_details` | gpt-4.1-mini-2025-04-14 | Error: Order not found | 55 |
| `get_order_details` | o4-mini-2025-04-16 | Error: Order not found | 52 |
| `exchange_delivered_order_items` | gpt-4.1-mini-2025-04-14 | Error: Non-delivered order cannot be exchanged | 43 |
| `find_user_id_by_name_zip` | gpt-4.1-mini-2025-04-14 | Error: User not found | 40 |
| `find_user_id_by_name_zip` | o4-mini-2025-04-16 | Error: User not found | 29 |
| `find_user_id_by_email` | o4-mini-2025-04-16 | Error: User not found | 29 |
| `find_user_id_by_email` | claude-3-7-sonnet-20250219 | Error: User not found | 28 |
| `find_user_id_by_email` | gpt-4.1-2025-04-14 | Error: User not found | 28 |
| `find_user_id_by_email` | gpt-4.1-mini-2025-04-14 | Error: User not found | 28 |
| `find_user_id_by_name_zip` | claude-3-7-sonnet-20250219 | Error: User not found | 26 |
| `modify_pending_order_items` | gpt-4.1-2025-04-14 | Error: The number of items to be exchanged should match | 21 |
| `return_delivered_order_items` | gpt-4.1-mini-2025-04-14 | Error: Payment method should be the original payment method | 20 |
