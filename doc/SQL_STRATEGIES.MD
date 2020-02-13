# MySQL / Percona 5.7 strategies 

## ORDER-REDUCE 

This is a strategy that can be useful to generate data for something, when the input data is a series of records, and the output should be also a series of records, aggregating the input in a way impossible to implement with simple GROUP BY + aggregate function.

The example problem will be calculating Action status segment data, where:
- input is a series of actions and joins/leaves to/from Member group / segment
- output is time spans when user was active, inactive, or not a member

I call this strategy ORDER-REDUCE because it is analogous to reduce in other programming languages. It means looping over the input, always taking 2 elements at a time, and updating some accumulator/state. It can be an alternative to creating temprary tables, which take a lot of time to write to disk.
Another benefit is at least a bit easier to understand format.

The general schema is:

1. Decide on grouping column from input (contact_id)
2. Decide on sequence column, by which we order records for each group (datetime of engagement or join)
3. Order the input data by (grouping, sequence). If this is one table, and you have the proper index, this will just read from the table without creating an intermediate materalized data!
4. Loop over pairs of rows:
  - do not compute (emit) data on 1 st row - it does not have any previous one to pair with
  - on every row, update accumulator variables, so next row (it's follower in pair) has it
  - compute (emit) data on the second row, using accumulator variables, 
  - mark emitted data on grouping change (new contact_id) or because they need to be emitted - remember to emit old grouping.
  - after all the loop is done, generate one last row of data (the last row did not have it following pair)
  - for emitting and accumulator variables, always use functions to compute them
5. Filter the result from unneded data (because all the rows will emit some data, exclude what is unnecessary)
  
In pesudocode:

```sql
SET @grouping := -1, @new_grouping := FALSE;
SET @accumulator1 := NULL, @accumulator2 := NULL

SELECT
contact_id, final_value1, final_value2, ... 
FROM
(
  SELECT 
    @new_grouping := IF (@grouping = contact_id, FALSE, TRUE),
    
    -- generate row based on PREVIOUS and THIS row
    @grouping as contact_id, -- PREVIOUS ROW VALUE
    emit_value1(attributes, @new_grouping, @accumulator1, ...) as final_value1,
    emit_value2(attributes, @accumulator2...) as final_value2,
  
    -- now updated the accumulators that carry over to next row
    @accumulator1 := accumulator1(attributes, @accumulator1),
    @accumulator2 := accumulator2(attributes, @accumulator2),

    @grouping := contact_id
  FROM 
  (
    SELECT 
      contact_id, timestamp, attributes
    ORDER BY
      contact_id, timestamp
  ) ordered_input_data
) reduced_data
WHERE exclude_unnecessary rows;

-- final step
SELECT 
```
