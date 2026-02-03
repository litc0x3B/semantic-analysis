using Npgsql;
using YuGiOhDomain;

string connectionString = "Host=localhost;Username=user;Password=password;Database=yugioh";
var generator = new SqlBatchGenerator();
var loader = new SqlLoader();

try
{
    using var conn = new NpgsqlConnection(connectionString);
    conn.Open();

    // ==================================================================================
    // 1. CLEANUP
    // ==================================================================================
    Console.WriteLine("Step 1: Cleaning up database...");
    using (var cleanupCmd = new NpgsqlCommand("TRUNCATE TABLE Duelists, Duels, Rounds, DuelParticipants RESTART IDENTITY CASCADE;", conn))
    {
        cleanupCmd.ExecuteNonQuery();
    }
    Console.WriteLine("Database is clean.");
    Console.WriteLine();

    // ==================================================================================
    // 2. SEED INITIAL DATA
    // ==================================================================================
    Console.WriteLine("Step 2: Seeding initial data...");

    var yugi = new Duelist("Yugi Muto") { Id = 1, State = EntityState.Added };
    var kaiba = new Duelist("Seto Kaiba") { Id = 2, State = EntityState.Added };
    var joey = new Duelist("Joey Wheeler") { Id = 3, State = EntityState.Added };

    var duel1 = new Duel { Id = 1, State = EntityState.Added };
    
    var p1 = new DuelParticipation(duel1, yugi) { State = EntityState.Added };
    var p2 = new DuelParticipation(duel1, kaiba) { State = EntityState.Added };

    var r1 = new Round(1, duel1) { Id = 1, State = EntityState.Added, WinnerId = yugi.Id };
    var r2 = new Round(2, duel1) { Id = 2, State = EntityState.Added, WinnerId = kaiba.Id };

    var duelists = new List<Duelist> { yugi, kaiba, joey };
    var duels = new List<Duel> { duel1 };
    var rounds = new List<Round> { r1, r2 };
    var parts = new List<DuelParticipation> { p1, p2 };

    var seedScript = generator.GenerateCommitScript(duelists, duels, rounds, parts);
    
    using (var cmd = new NpgsqlCommand(seedScript, conn))
    {
        cmd.ExecuteNonQuery();
    }
    Console.WriteLine("Initial data seeded successfully.");
    
    foreach(var e in duelists) e.State = EntityState.Unchanged;
    foreach(var e in duels) e.State = EntityState.Unchanged;
    foreach(var e in rounds) e.State = EntityState.Unchanged;
    foreach(var e in parts) e.State = EntityState.Unchanged;

    // ==================================================================================
    // 3. PAUSE FOR VERIFICATION
    // ==================================================================================
    Console.WriteLine("\n[ACTION REQUIRED] Check the database now to verify initial data.");
    Console.WriteLine("Press ENTER to proceed with modifications...");
    Console.ReadLine();

    // ==================================================================================
    // 4. APPLY CHANGES
    // ==================================================================================
    Console.WriteLine("Step 4: Applying changes (Add, Modify, Delete)...");

    yugi.Nickname = "Yami Yugi";
    yugi.State = EntityState.Modified;

    joey.State = EntityState.Deleted;

    var pegasus = new Duelist("Maximillion Pegasus") { Id = 4, State = EntityState.Added };
    duelists.Add(pegasus);

    var duel2 = new Duel { Id = 2, State = EntityState.Added };
    duels.Add(duel2);

    var p3 = new DuelParticipation(duel2, yugi) { State = EntityState.Added };
    var p4 = new DuelParticipation(duel2, pegasus) { State = EntityState.Added };
    parts.Add(p3);
    parts.Add(p4);

    var r3 = new Round(1, duel2) { Id = 3, State = EntityState.Added };
    rounds.Add(r3);

    r2.State = EntityState.Deleted;

    // ==================================================================================
    // 5. GENERATE & EXECUTE UPDATE SCRIPT
    // ==================================================================================
    Console.WriteLine("\nStep 5: Generating SQL for changes...");
    var updateScript = generator.GenerateCommitScript(duelists, duels, rounds, parts);

    Console.WriteLine("--- Generated Update Script ---");
    Console.WriteLine(updateScript);
    Console.WriteLine("-------------------------------\n");

    using (var cmd = new NpgsqlCommand(updateScript, conn))
    {
        int rows = cmd.ExecuteNonQuery();
        Console.WriteLine($"Updates executed. Rows affected: {rows}");
    }

    // ==================================================================================
    // 6. FINAL VERIFICATION
    // ==================================================================================
    Console.WriteLine("\nStep 6: Verifying final state...");
    loader.LoadFullGraph(conn, out var loadedDuelists, out var loadedDuels);

    Console.WriteLine($"\nFinal Database State:");
    Console.WriteLine($"Duelists ({loadedDuelists.Count}):");
    foreach (var d in loadedDuelists)
    {
        Console.WriteLine($" - [{d.Id}] {d.Nickname}");
    }

    Console.WriteLine($"\nDuels ({loadedDuels.Count}):");
    foreach (var d in loadedDuels)
    {
        Console.WriteLine($" - Duel [{d.Id}]");
        Console.WriteLine($"   Participants: {string.Join(", ", d.Participations.Select(p => p.Duelist.Nickname))}");
        Console.WriteLine($"   Rounds: {d.Rounds.Count}");
        foreach(var r in d.Rounds)
        {
            Console.WriteLine($"     > Round {r.Number}: Winner={(r.Winner?.Nickname ?? "None")}");
        }
    }
}
catch (Exception ex)
{
    Console.WriteLine($"CRITICAL ERROR: {ex.Message}");
    Console.WriteLine(ex.StackTrace);
}
