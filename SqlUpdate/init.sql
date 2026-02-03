CREATE TABLE Duelists (
    Id INT PRIMARY KEY,
    Nickname TEXT NOT NULL
);

CREATE TABLE Duels (
    Id INT PRIMARY KEY
);

CREATE TABLE DuelParticipants (
    DuelId INT NOT NULL,
    DuelistId INT NOT NULL,
    PRIMARY KEY (DuelId, DuelistId),
    FOREIGN KEY (DuelId) REFERENCES Duels(Id),
    FOREIGN KEY (DuelistId) REFERENCES Duelists(Id)
);

CREATE TABLE Rounds (
    Id SERIAL PRIMARY KEY,
    Number INT NOT NULL,
    DuelId INT NOT NULL,
    WinnerId INT,
    FOREIGN KEY (DuelId) REFERENCES Duels(Id),
    FOREIGN KEY (WinnerId) REFERENCES Duelists(Id)
);
