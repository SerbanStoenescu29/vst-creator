#pragma once

#include <JuceHeader.h>
#include "PluginProcessor.h"

class SimpleDelayAudioProcessorEditor final : public juce::AudioProcessorEditor
{
public:
    explicit SimpleDelayAudioProcessorEditor(SimpleDelayAudioProcessor&);
    ~SimpleDelayAudioProcessorEditor() override = default;

    void paint(juce::Graphics&) override;
    void resized() override;

private:
    SimpleDelayAudioProcessor& processor;

    juce::Slider delayTimeSlider;
    juce::Label delayTimeLabel;
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> delayTimeAttachment;

    juce::Slider mixSlider;
    juce::Label mixLabel;
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> mixAttachment;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(SimpleDelayAudioProcessorEditor)
};
