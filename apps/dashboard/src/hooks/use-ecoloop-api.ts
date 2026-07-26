"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ecoloopApi } from "@/lib/api/client";
import type { SimulationSummary } from "@/lib/api/schemas";

export function useBuildingsQuery() {
  return useQuery({
    queryKey: ["buildings"],
    queryFn: ecoloopApi.listBuildings
  });
}

export function useBuildingDetailsQuery(buildingId: string | null) {
  return useQuery({
    queryKey: ["buildings", "details", buildingId],
    queryFn: async () => {
      if (!buildingId) {
        throw new Error("A building identifier is required.");
      }

      return ecoloopApi.getBuilding(buildingId);
    },
    enabled: buildingId !== null
  });
}

export function useCreateBuildingMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ecoloopApi.createBuilding,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["buildings"] });
    }
  });
}

export function useSimulationListQuery() {
  return useQuery({
    queryKey: ["simulations"],
    queryFn: ecoloopApi.listSimulations
  });
}

export function useSimulationDetailsQuery(items: SimulationSummary[] | undefined) {
  const ids = [...(items ?? [])].map((item) => item.simulation_id).sort();
  return useQuery({
    queryKey: ["simulations", "details", ids],
    queryFn: async () => Promise.all(ids.map((id) => ecoloopApi.getSimulation(id))),
    enabled: ids.length > 0
  });
}

export function useRunSimulationMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ecoloopApi.runSimulation,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["simulations"] }),
        queryClient.invalidateQueries({ queryKey: ["buildings"] })
      ]);
    }
  });
}

export function useAiChatMutation() {
  return useMutation({
    mutationFn: ecoloopApi.runAiChat
  });
}

export function useGenerateReportMutation() {
  return useMutation({
    mutationFn: ecoloopApi.generateReport
  });
}
