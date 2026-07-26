import {
  buildDashboardSummary,
  compareSimulations,
  createComfortChartData,
  createEnergyTrendData,
  createHvacUsageData,
  getAverageComfortScore,
  getEstimatedCarbonReduction,
  getTotalEnergySaved
} from "@/lib/api/insights";
import {
  buildingListFixture,
  createSimulationDetail,
  simulationDetailsFixture
} from "@/test/fixtures";

describe("dashboard insights", () => {
  it("calculates energy savings across simulations", () => {
    expect(getTotalEnergySaved(simulationDetailsFixture)).toBe(620.6000000000004);
  });

  it("calculates average comfort score", () => {
    expect(getAverageComfortScore(simulationDetailsFixture)).toBeCloseTo(91.3, 1);
  });

  it("estimates carbon reduction from energy savings", () => {
    expect(getEstimatedCarbonReduction(simulationDetailsFixture)).toBeCloseTo(260.652, 3);
  });

  it("creates chart-ready energy trend data in chronological order", () => {
    const data = createEnergyTrendData([...simulationDetailsFixture].reverse());

    expect(data).toHaveLength(2);
    expect(data[0]).toMatchObject({
      name: "Jul 26",
      energy: 15420.6
    });
    expect(data[1]).toMatchObject({
      name: "Jul 27",
      electricity: 9020
    });
  });

  it("creates hvac and comfort chart datasets", () => {
    expect(createHvacUsageData(simulationDetailsFixture)[0]).toMatchObject({
      heating: 2410.4,
      cooling: 3188.1,
      equipment: 744
    });

    expect(createComfortChartData(simulationDetailsFixture)[1]).toMatchObject({
      temperature: 22.8,
      humidity: 48.2,
      score: 92.4
    });
  });

  it("builds dashboard summary cards", () => {
    expect(buildDashboardSummary(buildingListFixture, simulationDetailsFixture)).toEqual({
      totalBuildings: 1,
      totalSimulations: 2,
      energySaved: 620.6000000000004,
      comfortScore: 91.3,
      carbonReduction: 260.65200000000016
    });
  });

  it("compares baseline and candidate simulations", () => {
    const baseline = createSimulationDetail();
    const candidate = createSimulationDetail({
      id: "33333333-3333-3333-3333-333333333333",
      siteEnergy: 14800,
      hvac: 5200,
      comfortPpd: 7.6
    });

    expect(compareSimulations(baseline, candidate)).toEqual({
      energyDelta: -620.6000000000004,
      hvacDelta: -398.5,
      comfortDelta: -2.200000000000001
    });
  });
});
