using Npgsql;
using System;
using System.Collections.Generic;
using System.Linq;

namespace YuGiOhDomain
{
    public class SqlLoader
    {
        public List<Duelist> LoadDuelists(NpgsqlConnection conn)
        {
            var list = new List<Duelist>();
            using var cmd = new NpgsqlCommand("SELECT Id, Nickname FROM Duelists", conn);
            using var reader = cmd.ExecuteReader();
            while (reader.Read())
            {
                var id = reader.GetInt32(0);
                var nickname = reader.GetString(1);
                var d = new Duelist(nickname) { Id = id, State = EntityState.Unchanged };
                list.Add(d);
            }
            return list;
        }

        public List<Duel> LoadDuels(NpgsqlConnection conn)
        {
            var list = new List<Duel>();
            using var cmd = new NpgsqlCommand("SELECT Id FROM Duels", conn);
            using var reader = cmd.ExecuteReader();
            while (reader.Read())
            {
                var id = reader.GetInt32(0);
                var d = new Duel { Id = id, State = EntityState.Unchanged };
                list.Add(d);
            }
            return list;
        }

        public List<Round> LoadRounds(NpgsqlConnection conn)
        {
            var list = new List<Round>();
            using var cmd = new NpgsqlCommand("SELECT Id, Number, DuelId, WinnerId FROM Rounds", conn);
            using var reader = cmd.ExecuteReader();
            while (reader.Read())
            {
                var id = reader.GetInt32(0);
                var number = reader.GetInt32(1);
                var duelId = reader.GetInt32(2);
                int? winnerId = reader.IsDBNull(3) ? null : reader.GetInt32(3);

                
                var placeholderDuel = new Duel { Id = duelId }; 
                
                var r = new Round(number, placeholderDuel) 
                { 
                    Id = id, 
                    WinnerId = winnerId,
                    State = EntityState.Unchanged 
                };
                list.Add(r);
            }
            return list;
        }

        public List<DuelParticipation> LoadParticipations(NpgsqlConnection conn)
        {
            var list = new List<DuelParticipation>();
            using var cmd = new NpgsqlCommand("SELECT DuelId, DuelistId FROM DuelParticipants", conn);
            using var reader = cmd.ExecuteReader();
            while (reader.Read())
            {
                var duelId = reader.GetInt32(0);
                var duelistId = reader.GetInt32(1);

                var placeholderDuel = new Duel { Id = duelId };
                var placeholderDuelist = new Duelist("") { Id = duelistId };

                var p = new DuelParticipation(placeholderDuel, placeholderDuelist) 
                { 
                    State = EntityState.Unchanged 
                };
                list.Add(p);
            }
            return list;
        }

        public void LoadFullGraph(NpgsqlConnection conn, out List<Duelist> duelists, out List<Duel> duels)
        {
            duelists = LoadDuelists(conn);
            var rawDuels = LoadDuels(conn);
            var rawRounds = LoadRounds(conn);
            var rawParticipations = LoadParticipations(conn);

            var duelistDict = duelists.ToDictionary(d => d.Id);
            var duelDict = rawDuels.ToDictionary(d => d.Id);

            foreach (var r in rawRounds)
            {
                if (duelDict.TryGetValue(r.Duel.Id, out var realDuel))
                {
                    r.Duel = realDuel;
                    realDuel.Rounds.Add(r);
                }
                
                if (r.WinnerId.HasValue && duelistDict.TryGetValue(r.WinnerId.Value, out var realWinner))
                {
                    r.Winner = realWinner;
                    realWinner.WonRounds.Add(r);
                }
            }

            foreach (var p in rawParticipations)
            {
                if (duelDict.TryGetValue(p.DuelId, out var realDuel) && 
                    duelistDict.TryGetValue(p.DuelistId, out var realDuelist))
                {
                    p.Duel = realDuel;
                    p.Duelist = realDuelist;
                    
                    realDuel.Participations.Add(p);
                    realDuelist.Participations.Add(p);
                }
            }

            duels = rawDuels;
        }
    }
}
